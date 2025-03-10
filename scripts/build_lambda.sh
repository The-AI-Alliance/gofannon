#!/bin/bash

app_id=$3
build_root=$1
python_version=$2


build_path=$build_root/build
# TODO: Validate parameters


if test -d $build_root; then
    echo "Build root already exists. Exiting."
    exit 1
fi
dir_error=$(mkdir -p "$build_path" 2>&1)
if [ $? -ne 0 ]; then
    echo "Unable to create .zip archive build root directory $build_root. Reason: $dir_error. Exiting."
    exit 1
fi

poetry config warnings.export false

# We need a lock file here, otherwise requirements.txt will be malformed with text at the top of th file
poetry_error=$(poetry export -f requirements.txt --without-hashes >"$build_path"/requirements.txt 2>&1) 
if [ $? -ne 0 ]; then
    echo "Unable to export requirements.txt from project dependencies. Reason: $poetry_error. Cleaning up and xiting."
    rm -rf $build_root 2>&1 > /dev/null
    exit 1
fi

requirements_path=$build_path"/requirements.txt"

pip_error=$(pip install --platform manylinux2014_x86_64 --target=$build_path --implementation cp --python-version $python_version --only-binary=:all: --upgrade --no-compile -r $requirements_path 2>&1 >/dev/null)
if [ $? -ne 0 ]; then
    echo "'pip install' into the .zip archive build directory failed. Reason: $pip_error. Cleaning up and exiting."
    rm -rf $build_root 2>&1 > /dev/null
    exit 1
fi

rm $requirements_path
gofannon_error=$(cp -r ../../gofannon $build_path/)
if [ $? -ne 0 ]; then
    echo "copy project root to .zip archive build directory failed. Reason: $gofannon_error. Cleaning up and exiting."
    rm -rf $build_root 2>&1 > /dev/null
    exit 1
fi

archive=$build_root/"$app_id"_deployment_package.zip

# Per the AWS docs...
chmod -R 755 $build_root
rm -rf $build_path/__pycache__
zip_error=$( (cd $build_path && zip -r $archive . 2>&1 >/dev/null) )
if [ $? -ne 0 ]; then
    echo "zipping .zip archive from build directory failed. Reason: $zip_error. Cleaning up and exiting."
    rm -rf $build_root 2>&1 > /dev/null
    exit 1
fi

rm -rf $build_path
echo $archive
exit 0