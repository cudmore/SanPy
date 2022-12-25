
# Install on m1 arch arm64

Install mini conda from ‘Miniconda3-latest-MacOSX-arm64.pkg’

SHA256 hash: 0cb5165ca751e827d91a4ae6823bfda24d22c398a0b3b01213e57377a2c54226

see: https://docs.conda.io/en/latest/miniconda.html

Using Conda 4.12.0

/opt/miniconda3/bin/python

Python 3.9.12


```
conda create -y -n napari-env python=3.9
conda activate napari-env
conda install pyqt  # not PyQt5 like with pip
pip install napari
```

# install SanPy

```
conda create -y -n sanpy1-env python=3.9
conda activate sanpy1-env

pip install -e .
```

```
pip install --upgrade pip setuptools
```

setuptools 61.2.0 -->> 62.4.0
pip 21.2.4 -->> 22.1.2 (???)

# not PyQt5 like with pip
conda install pyqt 

# this would be 'pip install tables' but fails on arm
conda install pytables

pip install -e .
pip install -e .\[gui\]
pip install -e .\[dev\]

# need to add these to setup.cfg
#pip install pyqtgraph qdarkstyle 


# configure ssh

Three steps

1) https://docs.github.com/en/authentication/connecting-to-github-with-ssh/checking-for-existing-ssh-keys

2) https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent

3) https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account


ls -al ~/.ssh       # might not exists
ssh-keygen -t ed25519 -C “robert.cudmore@gmail.com"
eval "$(ssh-agent -s)"  
open ~/.ssh/config
touch ~/.ssh/config 
pico ~/.ssh/config  

```
Host *
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/id_ed25519
```

ssh-add -K ~/.ssh/id_ed25519    
pbcopy < ~/.ssh/id_ed25519.pub        # copy to clipboard

Follow link (3) above to add the new key to the GitHub website


## Switch an old https local GitHub to new ssh

```
# to see current (Should have https)
git remote -v

git remote set-url origin git@github.com:cudmore/SanPy.git

# verify
git remote -v

## Configure vs code

The vs code outline panel is uselull. I always want to turn off showing Python variables.

In VS Code, open preferences, search for 'outline.showVariables', and turn it off.

