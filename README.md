[English](README.md) | [한국어](README.ko.md)

# VibeCulling

![VibeCulling Screenshot](./.github/assets/vibeculling_main.png)

## What it is
*   A simple culling tool for amateur photographers that works by moving photos into folders.
*   Cull your photos single-handedly, almost like playing a game, using WASD, number keys, and the spacebar.
*   Handles both JPG and RAW files together.
*   It's especially useful for the initial culling stage—right after transferring hundreds of photos from your camera's memory card to your PC, helping you quickly select the few dozen shots worth keeping.
*   Open-source, portable (no installation required), and 100% local (no internet connection needed).

## What it isn't
*   This is not a tool that works with ratings or flags.
*   It does not edit your images. It does not delete them. It does not edit EXIF data. It only moves them to the folders you specify.
*   Honestly, it's not super fast. This is particularly true when decoding RAW files to view them (which is why I recommend using the embedded preview images in RAW files). I've tried my best to make it as fast as possible, but this is the limit of my coding skills.
*   **This is not malware.** While this application is not code-signed (I haven't paid Microsoft or Apple for a developer certificate), it's completely safe to use. Windows or macOS might flag it as an untrusted app, but the entire source code is available on GitHub for review. You can also check the VirusTotal scan result for verification: https://www.virustotal.com/gui/file/13ce2e07d99c842ff8ba32e68f5c6c677e17cf390550bcc768c1524b60c8c2e1?nocache=1

## Why I made this
*   I'm a completely amateur dad photographer. I enjoy taking pictures, and I enjoy editing the good ones. But culling? It's tedious and boring. I've even found myself hesitating to press the shutter or avoiding burst mode just to escape the burden of culling later.
*   While I use Lightroom for editing my RAW files, it's too heavy on my laptop to use for culling. So, I only import the photos I truly love into Lightroom for editing.
*   What I needed was a very simple tool, and I didn't want to spend money on professional culling software. I looked for free, lightweight, and simple culling tools, but couldn't find one that was just right for me. So, I built this with the help of VibeCoding.

## Notes
1.  **Minimum System Requirements (Estimated):** 1920x1080 resolution, 8GB RAM, and probably a dual-core or quad-core CPU.
2.  This app was originally named "PhotoSort"(https://github.com/newboon/PhotoSort) and was tested with feedback from a few Korean camera users. I later found out that another app already used that name, and it also felt a bit uninspired. So, I added some essential features I had missed and re-released it under the new name, VibeCulling.
3.  For users who shoot in RAW only (without JPGs), I highly recommend using the "preview" option when loading your files. It's much faster and avoids compatibility issues. Due to limitations in the underlying libraries, RAW files from some cameras—such as Nikon (Z8, Z9), Canon (R5 Mark II), and Panasonic (S1R, S5)—may fail to decode or display with distorted colors. However, for Nikon and Canon, the embedded preview images have a high enough resolution that using them for culling should not be an issue. Unfortunately, Panasonic's preview images are smaller, so you will have to work with a lower-resolution view. It has also been confirmed that RAW files from Fujifilm cameras take an unusually long time to decode, likely due to the unique X-Trans sensor array.
4.  Functionally, it's unlikely this app will change significantly from its current state. I believe it now has the basic features a culling tool should have. More importantly, as the codebase has grown, it has become challenging for both me and the AI to add major new features. However, if anyone reports a bug, I will do my best to fix it.
5.  This project is open-source, and anyone is welcome to improve it. However, as I'm not very familiar with GitHub, it would probably be best to fork the project and proceed with it as a separate endeavor.
6.  Another issue is that I'm literally a coding novice who started creating this app without knowing general development methodologies, so all the code is contained in a single Python file (by the time I realized this was problematic, I had already become too accustomed to this approach). Moreover, since the comments are written in Korean, I'm concerned that this might make it difficult for others to participate.
7.  The only PC I have access to is a Windows laptop. While I've tried to make this app compatible with various system specs and resolutions, there will be limitations. It may not be fully optimized in terms of performance or design, especially the macOS version, which I cannot test myself.
8.  This app makes extensive use of caching (background loading), so it can be memory-intensive, particularly if you are working with high-resolution photos.


---

## How to Use

### 1. Load Your Photo Folder
<div align="center">
  <img src=".github/assets/1-folderload.webp" alt="Loading folder" style="margin-bottom: 20px;">
  <br><br><br>
</div>

### 2. Assign Your Sorting Folders
<div align="center">
  <img src=".github/assets/2-sortfolder.webp" alt="Setting sort folders" style="margin-bottom: 20px;">
  <br><br><br>
</div>

### 3. Cull with Your Left Hand (Keyboard)
<div align="center">
  <img src=".github/assets/3-lefthand.webp" alt="One-hand culling example (left hand)" style="margin-bottom: 20px;">
  <br><br><br>
</div>

### 4. Cull with Your Right Hand (Mouse)
<div align="center">
  <img src=".github/assets/4-righthand.webp" alt="One-hand culling example (right hand)" style="margin-bottom: 20px;">
  <br><br><br>
</div>

### 5. Zoom and Pan
<div align="center">
  <img src=".github/assets/5-zoom.webp" alt="Zoom feature" style="margin-bottom: 20px;">
  <br><br><br>
</div>

### 6. Compare Similar Shots
<div align="center">
  <img src=".github/assets/6-compare.webp" alt="Compare feature" style="margin-bottom: 20px;">
</div>

---

## Getting Started

You can download the latest version for Windows and macOS from the **[GitHub Releases page](https://github.com/newboon/VibeCulling/releases)**.

-   **Windows:** Download the `VibeCulling_vX.X.X_win.zip` file.
-   Extract the zip
-   Run `VibeCulling.exe` (no installation needed)
-   **macOS:** Download the `VibeCulling_vX.X.X_macOS.dmg.zip` file.


---

## License

This project is licensed under the GNU Affero General Public License Version 3 (AGPL-3.0).
This means you are free to use, modify, and distribute the software, but any modifications must be made available under the same license, including when the software is used to provide network services.
For more details, see the LICENSE file.