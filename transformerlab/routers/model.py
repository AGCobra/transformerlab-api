import json
import shutil
from typing import Annotated
import transformerlab.db as db
from fastapi import APIRouter, Body
from fastapi.responses import FileResponse
from fastchat.model.model_adapter import get_conversation_template
import os

from transformerlab.shared import shared
from transformerlab.shared import dirs

router = APIRouter(tags=["model"])


@router.get("/healthz")  # TODO: why isn't this /model/helathz?
async def healthz():
    return {"message": "OK"}


@router.get("/model/gallery")
async def model_gallery_list_all():
    with open(f"{dirs.TFL_SOURCE_CODE_DIR}/transformerlab/galleries/model-gallery.json") as f:
        gallery = json.load(f)

    local_models = await db.model_local_list()
    local_model_names = set(model['model_id'] for model in local_models)

    # Mark which models have been downloaded already. The huggingfacerepo is our model_id.
    for model in gallery:
        model['downloaded'] = True if model['huggingface_repo'] in local_model_names else False

    return gallery


@router.get("/model/gallery/{model_id}")
async def model_gallery(model_id: str):

    # convert "~~~"" in string to "/":
    model_id = model_id.replace("~~~", "/")

    with open(f"{dirs.TFL_SOURCE_CODE_DIR}/transformerlab/galleries/model-gallery.json") as f:
        gallery = json.load(f)

    result = None

    for model in gallery:
        if model['huggingface_repo'] == model_id:
            result = model
            break

    return result


@router.get(path="/model/login_to_huggingface")
async def login_to_huggingface():
    from huggingface_hub import login
    token = await db.config_get("HuggingfaceUserAccessToken")

    if token is None:
        return {"message": "HuggingfaceUserAccessToken not set"}

    # Note how login() works. When you login, huggingface_hub saves your token as a file to ~/.huggingface/token
    # and it is there forever, until you delete it. So you only need to login once and it
    # persists across sessions.
    # https://huggingface.co/docs/huggingface_hub/v0.19.3/en/package_reference/login#huggingface_hub.login

    try:
        login(token=token)
        return {"message": "OK"}
    except:
        return {"message": "Login failed"}


@router.get(path="/model/download_from_huggingface")
async def download_model_from_huggingface(model: str):
    """specify a specific model from huggingface to download
    This function will not be able to infer out description etc of the model
    since it is not in the gallery"""
    job_id = await db.job_create(type="DOWNLOAD_MODEL", status="STARTED",
                                 job_data='{}')

    args = [f"{dirs.TFL_SOURCE_CODE_DIR}/transformerlab/shared/download_huggingface_model.py",
            "--model_name", model]

    try:
        await shared.async_run_python_script_and_update_status(python_script=args, job_id=job_id, begin_string="Fetching")
    except Exception as e:
        await db.job_update(job_id=job_id, status="FAILED")
        return {"message": "Failed to download model"}

    # Now save this to the local database
    await model_local_create(id=model, name=model)
    return {"message": "success", "model": model, "job_id": job_id}


@router.get(path="/model/download_model_from_gallery")
async def download_model_from_gallery(gallery_id: str):
    """Provide a reference to a model in the gallery, and we will download it
    from huggingface"""

    # get all models from gallery
    with open(f"{dirs.TFL_SOURCE_CODE_DIR}/transformerlab/galleries/model-gallery.json") as f:
        gallery = json.load(f)

    gallery_entry = None

    # for each entry in the gallery, check if the model_id matches
    for model in gallery:
        if model['uniqueID'] == gallery_id:
            gallery_entry = model
            break
    else:
        return {"message": "Model not found in gallery"}

    hugging_face_id = gallery_entry['huggingface_repo']
    hugging_face_filename = gallery_entry.get("huggingface_filename", None)
    name = gallery_entry['name']

    job_id = await db.job_create(type="DOWNLOAD_MODEL", status="STARTED",
                                 job_data='{}')

    args = [f"{dirs.TFL_SOURCE_CODE_DIR}/transformerlab/shared/download_huggingface_model.py",
            "--model_name", hugging_face_id,
            ]

    try:
        process = await shared.async_run_python_script_and_update_status(python_script=args, job_id=job_id, begin_string="Fetching")
        exitcode = process.returncode
        print(f"exitcode: {exitcode}")
        if (exitcode != 0):
            await db.job_update(job_id=job_id, status="FAILED")
            return {"status": "error", "message": "Failed to download model"}
    except Exception as e:
        await db.job_update(job_id=job_id, status="FAILED")
        return {"status": "error", "message": "Failed to download model"}

    if hugging_face_filename is not None:
        args += ["--model_filename", hugging_face_filename]
    else:
        # only save to local database if we are downloading the whole repo
        await model_local_create(id=hugging_face_id, name=name, json_data=gallery_entry)

    return {"status": "success", "message": "success", "model": model, "job_id": job_id}


@router.get("/model/get_conversation_template")
async def get_model_prompt_template(model: str):
    # Below we grab the conversation template from FastChat's model adapter
    # solution by passing in the model name
    return get_conversation_template(model)

# get_models_dir
# Helper function to get the models directory and create it if it doesn't exist
# models are stored in separate subdirectories under workspace/models


def get_models_dir():
    models_dir = dirs.MODELS_DIR

    # make models directory if it does not exist:
    if not os.path.exists(f"{models_dir}"):
        os.makedirs(f"{models_dir}")

    return models_dir


@router.get("/model/list")
async def model_local_list():

    # the model list is a combination of downloaded hugging face models and locally generated models
    # start with the list of downloaded models which is stored in the db
    models = await db.model_local_list()

    # now generate a list of local models by reading the filesystem
    models_dir = get_models_dir()

    # now iterate through all the subdirectories in the models directory
    with os.scandir(models_dir) as dirlist:
        for entry in dirlist:
            if entry.is_dir():

                # Look for model information in info.json
                info_file = os.path.join(models_dir, entry, "info.json")
                try:
                    with open(info_file, "r") as f:
                        filedata = json.load(f)
                        f.close()

                        # NOTE: In some places info.json may be a list and in others not
                        # Once info.json format is finalized we can remove this
                        if isinstance(filedata, list):
                            filedata = filedata[0]

                        # tells the app this model was loaded from workspace directory
                        filedata["stored_in_filesystem"] = True

                        # Set local_path to the filesystem location
                        # this will tell Hugging Face to not try downloading
                        filedata["local_path"] = os.path.join(
                            models_dir, entry)

                        # Some models are a single file (possibly of many in a directory, e.g. GGUF)
                        # For models that have model_filename set we should link directly to that specific file
                        if ("model_filename" in filedata and filedata["model_filename"]):
                            filedata["local_path"] = os.path.join(
                                filedata["local_path"], filedata["model_filename"])

                        models.append(filedata)

                except FileNotFoundError:
                    # do nothing: just ignore this directory
                    pass

    return models


@router.get("/model/create")
async def model_local_create(id: str, name: str, json_data={}):
    await db.model_local_create(model_id=id, name=name, json_data=json_data)
    return {"message": "model created"}


@router.get("/model/delete")
async def model_local_delete(model_id: str):
    # If this is a locally generated model then actually delete from filesystem
    # Check for the model stored in a directory based on the model name (i.e. the part after teh slash)
    root_models_dir = get_models_dir()
    model_dir = model_id.rsplit('/', 1)[-1]
    info_file = os.path.join(root_models_dir, model_dir, "info.json")
    if (os.path.isfile(info_file)):
        model_path = os.path.join(root_models_dir, model_dir)
        print(f"Deleteing {model_path}")
        shutil.rmtree(model_path)

    else:
        # If this is a hugging face model then delete from the database but leave in the cache
        print(
            f"Deleting model {model_id}. Note that this will not free up space because it remains in the HuggingFace cache.")
        print("If you want to delete the model from the HuggingFace cache, you must delete it from:")
        print("~/.cache/huggingface/hub/")

    # Delete from the database
    await db.model_local_delete(model_id=model_id)
    return {"message": "model deleted"}


@router.post("/model/pefts")
async def model_gets_pefts(model_id: Annotated[str, Body()],):
    workspace_dir = dirs.WORKSPACE_DIR
    adaptors_dir = f"{workspace_dir}/adaptors/{model_id}"
    adaptors = []
    if (os.path.exists(adaptors_dir)):
        adaptors = os.listdir(adaptors_dir)
    return adaptors


@router.get("/model/delete_peft")
async def model_delete_peft(model_id: str, peft: str):
    workspace_dir = dirs.WORKSPACE_DIR
    adaptors_dir = f"{workspace_dir}/adaptors/{model_id}"
    peft_path = f"{adaptors_dir}/{peft}"
    shutil.rmtree(peft_path)
    return {"message": "success"}
