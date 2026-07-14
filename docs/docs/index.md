SanPy is software to perform analysis of whole-cell curent clamp recordings. It is designed to work on a range of excitable cells including cardiac myocytes and neurons.

Historically, it was originally designed for spontaneous [cardiac action potentials][cardiac action potential] from [whole-cell current-clamp][patch-clamp] recordings of [cardiac myocytes]. Now, we have extended it to include the analysis of neuronal action potentials.

If you find the code in this repository interesting, please email Robert Cudmore at robert.cudmore@gmail.com and we can get you started. We are always looking for users and collaborators.

## Key features:

- Easy to use [desktop application](desktop-application) with a growing number of built in [plugins](plugins).

- An [API](api/overview) for full control of all aspects of file loading and analysis all from your own Python scripts.

- An extensible [plugin](api/writing-a-plugin.md) architecture providing a wide range of pre-built plugins. We invite the community to build their own.

- An extensible [file loader](api/writing-a-file-loader.md) architecture so any type of raw data can be opened. We provide file loaders for Molecular Devices (Axon Instruments) abf and atf file formats (using pyAbf), as well as general purpose comma-seperated-value files (csv).

- A rich range of [analysis results](methods/#analysis-results) such as spike threshold detection, interval statistics, and spike shape analysis. Like the plugin and file loading architecures, SanPy also provide a software architecute to add [new analysis](api/writing-new-analysis.md) measurements.

## [Desktop Application](desktop-application)
<IMG SRC="img/sanpy-pyqt-1.png" width=700>

## [Plugins](plugins)
<IMG SRC="img/sanpy-plugin-overview.png" width=700>

<!-- <table>
<tr>
    <td>
    <IMG SRC="img/plugins/plot-recording.png" width=300>
    </td>
    <td>
    <IMG SRC="img/plugins/spike-clips.png" width=300>
    </td>
</tr>
<tr>
    <td>
    <IMG SRC="img/plugins/plot-fi.png" width=300>
    </td>
    <td>
    <IMG SRC="img/plugins/scatter-plot.png" width=300>
    </td>
</tr>
</table> -->

## SanPy Manuscripts

:   Guarina L, Johnson TL, Griffith T, Santana LF, **Cudmore RH** (2024) SanPy: Software for the analysis and visualization of whole-cell current-clamp recordings. Biophys J, 2;123(7):759-769. doi: 10.1016/j.bpj.2024.02.025. [PubMed: 38419330](https://pubmed.ncbi.nlm.nih.gov/38419330/).

:   SanPy was originally described in a bioRxiv manuscript 2023.05.06.539660; doi: [https://doi.org/10.1101/2023.05.06.539660](https://doi.org/10.1101/2023.05.06.539660).


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
