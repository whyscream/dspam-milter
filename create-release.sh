#!/bin/sh

# An automated way to create a new release

version=$1
branch=$2

test -z "$version" && echo "No version specified!" && exit 1
test -z "$branch" && echo "No branch specified!" && exit 1

if ! git checkout release; then
  echo "Failed to switch to release branch" && exit 1

elif ! git merge --no-ff "$branch"; then
  echo "Failed to merge branch '$branch' into 'release'" && exit 1

elif ! sed -i "s/^VERSION = '.*'$/VERSION = '$version'/" dspam/__init__.py; then
  echo "Failed to set new version number in project" && exit 1

elif ! sed -i "s/version = '.*',$/version = '$version',/" setup.py; then
  echo "Failed to set new version number in setup.py" && exit 1

elif ! git commit -m "Set version to $version" dspam/__init__.py setup.py; then
  echo "Failed to commit new version" && exit 1

elif ! git tag -m "Release $version" "$version"; then
  echo "Failed to tag new release" && exit 1

fi

echo "Created new tag for release '$version'"
