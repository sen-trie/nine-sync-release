# Installation

## Requirements

- Blender **5.3+**
- [mmd_tools](https://extensions.blender.org/add-ons/mmd-tools/) **4.5.5+** (install and enable it separately)

## Install NineSync from Blender

1. Open **Edit > Preferences > Get Extensions**.
2. Open the repository menu and choose **Add Remote Repository**.
3. Enter `https://sen-trie.github.io/nine-sync-release/index.json`.
4. Find **NineSync** and install it.
5. Open the **3D Viewport**, press **N**, and find the **NineSync** tab.

Alternatively, download the combined extension ZIP from [NineSync Releases](https://github.com/sen-trie/nine-sync-release/releases) and install it with **Install from Disk**.

<!-- prettier-ignore -->
!!! warning "One install only"
    Use the combined NineSync extension as the normal installation. Do not install it alongside the standalone PMM Bridge and FX Importer add-ons.

## Getting started

1. Open the NineSync panel and choose a `.pmm` project in **Source PMM**.
2. Press the refresh icon next to **PMX Models** and set each model's **Target**.
3. Select **Sync Now**.

For accessories without a PMM, use **File > Import > MMD Accessory (.x)**.
