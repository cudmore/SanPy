
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


conda create -y -n sanpy-env python=3.9
conda activate sanpy-env

pip install --upgrade pip

conda install pyqt # not PyQt5 like with pip

# this would be 'pip install tables' but fails on arm
conda install pytables

pip install -e .

# need to add these to setup.cfg
pip install pyqtgraph qdarkstyle 


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
git remote -v. # to see current (Should have https)

git remote set-url origin git@github.com:USERNAME/REPOSITORY.git

Git remote -v. # to verify

## Configure vs code

The vs code outline panel is uselull. I always want to turn off showing Python variables.

In VS Code, open preferences, search for 'outline.showVariables', and turn it off.

