# GitHub web-only recovery (Mac / Chrome)

If Finder hides `.github`, you can still rebuild the repository entirely in GitHub's web interface.

1. Unzip `M9Cam_Git_Recovery_v2_67.zip` on your Mac.
2. Create a new empty GitHub repository.
3. Use **Add file → Upload files** and upload the visible files/folders from `M9Cam_Git_Recovery_v2_67`.
4. In GitHub choose **Add file → Create new file**.
5. Enter this filename exactly:

   `.github/workflows/build-m9cam.yml`

6. Open `GITHUB_WORKFLOW_build-m9cam.yml` from the recovery folder, copy all of it, and paste it into the GitHub editor.
7. Commit the new workflow file.
8. You may delete the visible root copy `GITHUB_WORKFLOW_build-m9cam.yml` afterward; it is only a convenience copy.
9. Open **Actions → Build recovered M9Cam PERF3I → Run workflow**.
10. Download the APK artifact when the workflow succeeds.

The Actions workflow records the PhotonCamera `dev` commit used for the build in `PHOTON_UPSTREAM_COMMIT.txt` so the new repository can be pinned later.
