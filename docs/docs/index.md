SanPy is software to perform analysis of whole-cell curent clamp recording. 

It was originally designed for spontaneous [cardiac action potentials][cardiac action potential] from [whole-cell current-clamp][patch-clamp] recordings of [cardiac myocytes]

This is a work-in-progress and under heavy development. If you find the code in this repository interesting, please email Robert Cudmore at UC Davis (rhcudmore@ucdavis.edu) and we can get you started. We are looking for users and collaborators.

Key features:

1) Easy to use [desktop application](desktop-application).

2) We have implemented a [plugin](plugins) architecture, provide a number of plugins and invite the community to build their own.

3) We have also made [file loader](file-loaders) plugins so any type of raw data can be opened. We provide file loaders for Molecular Devices (Axon Instruments) abf and atf file formats, as well as general purpose comma-seperated-value files (csv).

4) We have implemented the most common analysis measurements such as spike threshold detection, interval statistics, and spike shape analysis. Like our plugin and file loading architecures, we also provide a simple plugin system to add [new analysis](user-analysis) measurements.

## Desktop Application

<IMG SRC="img/sanpy-pyqt-1.png" width=900>

## Plugins

<IMG SRC="img/plugins/scatter-plot.png" width=700>

<!-- ### On the web -->

<!-- <IMG SRC="img/dash-june4.png" width=900 border=1> -->

<!--
## For anyone interested

SanPy is pronounced ['senpai']['senpai']
-->

[cardiac action potential]: https://en.wikipedia.org/wiki/Cardiac_action_potential
[cardiac myocytes]: https://en.wikipedia.org/wiki/Cardiac_muscle_cell
[patch-clamp]: https://en.wikipedia.org/wiki/Patch_clamp

['senpai']: https://en.wikipedia.org/wiki/Senpai_and_k%C5%8Dhai
