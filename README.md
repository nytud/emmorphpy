# emMorphPy
A wrapper, a lemmatizer and REST API implemented in Python for ___emMorph__ (Humor) Hungarian morphological analyzer_ 

## Requirements

  - (Already in the repository) The compiled FST (hu.hfstol): go to https://github.com/dlt-rilmta/emMorph for compilation details
  - (Already in the repository) The lemmatizer config file: available at https://github.com/dlt-rilmta/hunlp-GATE/blob/master/Lang_Hungarian/resources/hfst/hfst-wrapper.props
  - _hfst-lookup 0.6 (hfst 3.13.0)_ or higher: On Ubuntu 18.04 LTS or higher just `sudo apt install hfst`
  - Python 3 (tested with 3.6)
  - Pip to install the additional requirements
  - (Optional) a cloud service like [Heroku](https://heroku.com) for hosting the API

## Install on local machine

  - Clone the repository
  - Run: `sudo pip3 install -r requirements.txt'
  - Use from Python!

## Install to Heroku

  - Register
  - Download Heroku CLI
  - Login to Heroku from the CLI
  - Create an app
  - Clone the repository
  - Add Heroku as remote origin
  - Add APT buildpack: `heroku buildpacks:add --index 1 https://github.com/heroku/heroku-buildpack-apt`
  - Push the repository to Heroku!
  - Enjoy!

## Usage

  - From browser or anyhow through the REST API:
     - Lemmatization: https://emmorph.herokuapp.com/stem/működik
     - Detailed analysis: https://emmorph.herokuapp.com/analyze/működik
     - Lemmatisation with the corresponding detailed analysis: https://emmorph.herokuapp.com/dstem/működik
  - From Python:

        import emmorphpy.emmorphpy as emmorph
        m = emmorph.EmMorphPy()
    	print(m.stem('működik')
    	print(m.analyse('működik')
    	print(m.dstem('működik')

## License

This Python wrapper, the lemmatizer and the REST API is licensed under the LGPL 3.0 license.
The database and the lemmatizer configuration has its own license!

