#!/bin/bash
set -e

VERSION="0.1.0"
ENV_NAME="transformerlab"


# This script is meant to be run  on a new computer. 
# It will pull down the API and install
# it at ~/.transfomerlab/src

abort() {
  printf "%s\n" "$@" >&2
  exit 1
}

# string formatters
if [[ -t 1 ]]
then
  tty_escape() { printf "\033[%sm" "$1"; }
else
  tty_escape() { :; }
fi
tty_mkbold() { tty_escape "1;$1"; }
tty_underline="$(tty_escape "4;39")"
tty_blue="$(tty_mkbold 34)"
tty_red="$(tty_mkbold 31)"
tty_bold="$(tty_mkbold 39)"
tty_reset="$(tty_escape 0)"

shell_join() {
  local arg
  printf "%s" "$1"
  shift
  for arg in "$@"
  do
    printf " "
    printf "%s" "${arg// /\ }"
  done
}

ohai() {
  printf "${tty_blue}==>${tty_bold} %s${tty_reset}\n" "$(shell_join "$@")"
}

warn() {
  printf "${tty_red}Warning${tty_reset}: %s\n" "$(chomp "$1")" >&2
}

# First check OS.
OS="$(uname)"
if [[ "${OS}" == "Linux" ]]
then
  TFL_ON_LINUX=1
elif [[ "${OS}" == "Darwin" ]]
then
  TFL_ON_MACOS=1
else
  abort "Tranformer Lab is only supported on macOS and Linux."
fi

TFL_DIR="$HOME/.transfomerlab/src"
TFL_GIT_REPO="https://github.com/transformerlab/transformerlab-api"

# Check if the user has installed the required tools.
if [[ -z "$(command -v git)" ]]
then
  # Right now this script depends on git but we could
  # change this to pull down a zip file instead from git
  # hub instead
  abort "Git is not installed. Please install Git and try again."
fi

# Check if the user has already installed Transformer Lab.
if [[ -d "${TFL_DIR}" ]]
then
  # Check what version has been installed by looking at the version file:
  if [[ -f "${TFL_DIR}/VERSION" ]]
  then
    INSTALLED_VERSION="$(cat "${TFL_DIR}/VERSION")"
  else
    INSTALLED_VERSION="unknown"
  fi
  # If the installed version is the same as the current version, then
  # we don't need to do anything, unless the user passes --force:
  if [[ "${INSTALLED_VERSION}" == "${VERSION}" ]]
  then
    if [[ "$1" == "--force" ]]
    then
      ohai "Transformer Lab ${VERSION} is already installed, but --force was passed."
      pushd "${TFL_DIR}"
      git pull
      popd
    else
      ohai "Transformer Lab ${VERSION} is already installed. Skipping Install."
    fi
  else
    # Otherwise, the user has an different version installed, so we should try to upgrade.
    ohai "Transformer Lab ${INSTALLED_VERSION} is already installed, but you have ${VERSION}."
    ohai "Upgrading to Transformer Lab ${VERSION} ..."
    pushd "${TFL_DIR}"
    git pull
    popd
  fi
else
  # If the user has not installed Transformer Lab, then we should install it.
  ohai "Installing Transformer Lab ${VERSION}..."
  # Clone the repository:
  git clone --depth=1 "${TFL_GIT_REPO}" "${TFL_DIR}"
fi

# Now time to install dependencies and requirements.txt by running
# the init.sh script.
INIT_SCRIPT="${TFL_DIR}/init.sh"

# check if conda environment already exists:
if ! command -v conda &> /dev/null; then
  echo "Conda is not installed."
  source "$INIT_SCRIPT"
else
  if { conda env list | grep "$ENV_NAME"; } >/dev/null 2>&1; then
    if [[ "$1" == "--force" ]]
    then
      ohai "Forcing conda dependencies to be reinstalled."
      source "$INIT_SCRIPT"
    else
      ohai "Conda dependencies look like they've been installed already."
    fi
  else
    ohai "Installing conda and conda dependencies..."
    source "$INIT_SCRIPT"
  fi
fi


ohai "Installation successful!"
echo "------------------------------------------"
echo "Transformer Lab is installed to:"
echo "  ${TFL_DIR}"
echo "You can run Transformer Lab with:"
echo "  conda activate ${ENV_NAME}"
echo "  ${TFL_DIR}/run.sh"
echo "------------------------------------------"
echo