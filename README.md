# emMorphPy
A wrapper and lemmatizer implemented in Python for ___emMorph__ (Humor) Hungarian morphological analyzer_ 

This branch can be used for deploying the application to herkou. See [master branch](https://github.com/dlt-rilmta/emmorphpy/tree/master) for other information

## Install to Heroku

  - Register
  - Download Heroku CLI
  - Login to Heroku from the CLI
  - Create an app
  - Clone the repository
  - Add Heroku as remote origin
  - Add APT buildpack: `heroku buildpacks:add --index 1 https://github.com/heroku/heroku-buildpack-apt`
  - Add Python buildpack: `heroku buildpacks:add --index 2 heroku/python`
  - Push this branch to Heroku
  - Enjoy!

## Usage

  - From browser or anyhow through the REST API:
     - Lemmatization: https://emmorph.herokuapp.com/stem/működik
     - Detailed analysis: https://emmorph.herokuapp.com/analyze/működik
     - Lemmatisation with the corresponding detailed analysis: https://emmorph.herokuapp.com/dstem/működik
     - The library also support HTTP POST requests to handle multiple words at once. (See examples for details.)

	```python
	>>> import requests
	>>> import json
	>>> word = 'működik'
	>>> json.loads(requests.get('https://emmorph.herokuapp.com/stem/' + word).text)[word]
	[{'lemma': 'működik', 'tag': '[/V][Prs.Def.3Pl]'}, {'lemma': 'működik', 'tag': '[/V][Prs.NDef.3Sg]'}]
	>>> json.loads(requests.get('https://emmorph.herokuapp.com/analyze/' + word).text)[word]
	[{'morphana': 'működik[/V]=működ+ik[Prs.Def.3Pl]=ik'}, {'morphana': 'működik[/V]=működ+ik[Prs.NDef.3Sg]=ik'}]
	>>> json.loads(requests.get('https://emmorph.herokuapp.com/dstem/' + word).text)[word]
    [{'lemma': 'működik', 'tag': '[/V][Prs.Def.3Pl]', 'morphana': 'működik[/V]=működ+ik[Prs.Def.3Pl]=ik', 'readable': 'működik[/V]=működ + ik[Prs.Def.3Pl]', 'twolevel': 'm:m ű:ű k:k ö:ö d:d :i :k :[/V] i:i k:k :[Prs.Def.3Pl]'}, {'lemma': 'működik', 'tag': '[/V][Prs.NDef.3Sg]', 'morphana': 'működik[/V]=működ+ik[Prs.NDef.3Sg]=ik', 'readable': 'működik[/V]=működ + ik[Prs.NDef.3Sg]', 'twolevel': 'm:m ű:ű k:k ö:ö d:d :i :k :[/V] i:i k:k :[Prs.NDef.3Sg]'}]
	>>> words = '\n'.join(('form', word, 'word2', ''))  # One word per line (first line is header, trailing newline is needed!)
	>>> words_out = requests.post('https://emmorph.herokuapp.com/stem', files={'file': words}).text.split('\n')
	>>> print(words_out[1].split('\t'))
	['működik', '[{"lemma": "működik", "tag": "[/V][Prs.Def.3Pl]"}, {"lemma": "működik", "tag": "[/V][Prs.NDef.3Sg]"}]']
	>>> words_out = requests.post('https://emmorph.herokuapp.com/analyze', files={'file': words}).text.split('\n')
	>>> print(words_out[1].split('\t'))
	['működik', '[{"morphana": "működik[/V]=működ+ik[Prs.Def.3Pl]=ik"}, {"morphana": "működik[/V]=működ+ik[Prs.NDef.3Sg]=ik"}]']
    >>> words_out = requests.post('https://emmorph.herokuapp.com/dstem', files={'file': words}).text.split('\n')
	>>> print(words_out[1].split('\t'))
	['működik', '[{"lemma": "működik", "tag": "[/V][Prs.Def.3Pl]", "morphana": "működik[/V]=működ+ik[Prs.Def.3Pl]=ik", "readable": "működik[/V]=működ + ik[Prs.Def.3Pl]", "twolevel": "m:m ű:ű k:k ö:ö d:d :i :k :[/V] i:i k:k :[Prs.Def.3Pl]"}, {"lemma": "működik", "tag": "[/V][Prs.NDef.3Sg]", "morphana": "működik[/V]=működ+ik[Prs.NDef.3Sg]=ik", "readable": "működik[/V]=működ + ik[Prs.NDef.3Sg]", "twolevel": "m:m ű:ű k:k ö:ö d:d :i :k :[/V] i:i k:k :[Prs.NDef.3Sg]"}]']
	```
 

## License

This Python wrapper, the lemmatizer implementation is licensed under the LGPL 3.0 license.
xtsv, HFST, the database and the lemmatizer configuration has their own license.
