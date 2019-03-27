## Requires

Python 3.7.x

## Install

    # download and extract .zip or clone with git
    git clone https://github.com/cudmore/bAnalysis.git
    
    cd spike-analysis
    pip install -r requirements.txt

## Run

    python src/AnalysisApp.py

## Building a standalong app (macOS)

Install pyinstaller

    pip install pyinstaller

Make the app

    cd src
    ./makeapp

## To Do

### 20190326

 - Save analysis csv file and reload when loading folder. Don't always require re-analysis. Will break when format of csv file changes, make sure to include a file version.
 - Implement all stats used by Larson ... Proenza (2013) paper.
 - Show average spike clip in red
 - Export average spike clip
 - Take all stats on average spike clip. Is it different from taking average across all spikes?
 