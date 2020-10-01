# Contributing

## Version bumping conventions

- This repository is using the [semver scheme](https://semver.org/) for versioning.
    Major, minor and patch levels must be explicitly written (e.g. 1.0.0)
- Version is to be bumped only when all tests are passed and new release is created (e.g. when the new feature is ready)
- Version changes only when the result or performance of the runinng the code changes for any input and output between commits.
    Documentation (excluding the main `README.md`) and build system improvements do not yield new version.
    These requirements may be ignored by common sense
- The _git tag_, the _version of the main program_ and the _version of the docker image_ must be matched for convenience.
    The version of the dependent modules must not match the version of the main program, but it is advised for them to be pinned for reproducible builds
- Please use `make release-major`, `make release-minor`, `make release-patch` to release a new version!

## Using the released module

When new release is created use the direct link of the released `.whl` file in the `requirements.txt` of the main program to update the module as dependency

## Notes on Continous Integration (CI)

The current settings allow new releases only on the master branch, when the commit is associated with a _git tag_ and the tag matches the semver scheme and the `__version__` variable of the module while all tests pass.
For other commits the CI system shows if testing is failed or passed

### Seting up CI with Travis-CI

1) Register at Travis-CI
2) Generate a [personal access token](https://github.com/settings/tokens/new) on github (for users only). Make sure that all subsidiaries of `Full control of private repositories` are checked
3) Save the generated token as `$GITHUB_TOKEN` environment variable in Travis-CI and enable the repository
4) Place an appropriate `.travis.yml` file in the root directory of the repository
5) Create a new commit to test
