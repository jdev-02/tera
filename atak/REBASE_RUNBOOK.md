# ATAK Plugin Branch — Rebase Runbook

**Audience:** Ben.
**When to use this:** if your `plugin` branch contains the vendored `atak/ATAK-CIV-5.7.0.3-SDK/` directory (1,564 files, ~117 MB, including `android_keystore` and `main.jar`). Branch `plugin` at commit `edb8d0c` is in this state as of Sat 2026-05-02 20:56 PT.

**Why rebase:**

1. The repo is **public**. Vendoring the ATAK-CIV SDK has redistribution-license implications (PAR Government / TAK Product Center). Your own `TERA_EXPORT_README.md` flagged this:
   > *"These two `tools/` files are local SDK artifacts and should not be committed to a public repo unless you have confirmed you are allowed to redistribute them."*
2. `android_keystore` was committed. Even a development keystore in a public repo is a security smell that won't pass review.
3. Repo is now ~205 MB; clones get slow; CI gets slow; future contributors pay forever.
4. Two single files (`main.jar` 31.6 MB, sample tile bundles 17–19 MB) are close to GitHub's 100 MB block ceiling. We're flying low.

**The fix:** keep your code (~25 KB), drop the SDK, ship a setup script for whoever clones.

---

## Final tree shape we want

```text
atak/
├── README.md                         # high-level: how to build the plugin
├── REBASE_RUNBOOK.md                 # this file (deletable after the rebase)
├── plugin/                           # NEW home for your work
│   ├── README.md                     # was TERA_EXPORT_README.md, paths updated
│   ├── template.local.properties     # NEW — points to operator's Android SDK
│   ├── build.gradle
│   ├── settings.gradle
│   ├── gradle.properties
│   ├── scripts/
│   │   ├── build_release.sh          # was TERA_EXPORT_BUILD_SCRIPT.sh
│   │   └── install_device.sh         # was TERA_EXPORT_INSTALL_SCRIPT.sh
│   ├── tools/
│   │   ├── README.md                 # was TERA_EXPORT_TOOLS_README.md
│   │   ├── USGS_Topo_TERA.xml
│   │   └── .gitkeep                  # SDK jars + keystore land here, gitignored
│   └── app/
│       ├── build.gradle
│       ├── proguard-gradle.txt
│       ├── proguard-gradle-repackage.txt
│       └── src/
│           ├── main/
│           │   ├── AndroidManifest.xml
│           │   ├── assets/plugin.xml
│           │   ├── java/TacticalEdgeRouteAgent/plugin/
│           │   │   ├── TERAPlugin.java
│           │   │   ├── TeraPlanClient.java
│           │   │   └── PluginNativeLoader.java
│           │   └── res/values/strings.xml
│           └── gov/res/values/strings.xml
├── __init__.py                       # already on main from #63
├── bridge.py                         # already on main from your #61
└── cot.py                            # already on main from your #61
```

`atak/ATAK-CIV-5.7.0.3-SDK/` directory: **gone entirely**. Operators who want to build the plugin download the SDK separately and drop the relevant artifacts into `atak/plugin/tools/` (gitignored) following `atak/plugin/README.md`.

---

## Step-by-step

Run these on **your laptop** (where you have the SDK + Android Studio + a known-good plugin build). The new `.gitignore` rules from PR jon/atak-sdk-guard will protect you from re-committing the SDK during this surgery — make sure that PR has merged to main first, or copy its `.gitignore` additions into your branch before you start.

### 0. Pre-flight

```bash
cd ~/hackathon-scaffold
git fetch origin
git switch plugin

# Confirm where you are (should match)
git log --oneline -3
# Expect: edb8d0c Add ATAK SDK plugin workspace
#         089da00 feat(routing): add local Valhalla and ATAK export backbone
#         (then divergence with main)

# Confirm the SDK directory exists and the keystore is on disk
ls atak/ATAK-CIV-5.7.0.3-SDK/android_keystore   # should print the path
```

### 1. Create a clean working branch

Don't rewrite `plugin` directly. Make a new branch and reshape there. If anything goes wrong, `plugin` is untouched.

```bash
git switch -c ben/atak-plugin-clean main
```

This puts you on a new branch off latest `main` (which has your `089da00` Valhalla/ATAK backbone already merged via the routing PR — verify with `git log --oneline -5 | grep 089d`; if it's not there, cherry-pick it: `git cherry-pick 089da00`).

### 2. Copy ONLY your work out of the SDK directory

You have a working SDK + plugin layout at `atak/ATAK-CIV-5.7.0.3-SDK/samples/plugintemplate/` on the `plugin` branch. We're going to extract just your files from there.

```bash
# Make the destination
mkdir -p atak/plugin/scripts atak/plugin/tools \
         atak/plugin/app/src/main/java/TacticalEdgeRouteAgent/plugin \
         atak/plugin/app/src/main/assets \
         atak/plugin/app/src/main/res/values \
         atak/plugin/app/src/gov/res/values

# Switch references to grab files FROM the plugin branch's SDK tree
SDK="atak/ATAK-CIV-5.7.0.3-SDK"
TPL="$SDK/samples/plugintemplate"

# Your Java source
git checkout plugin -- $TPL/app/src/main/java/TacticalEdgeRouteAgent/plugin/TERAPlugin.java
git checkout plugin -- $TPL/app/src/main/java/TacticalEdgeRouteAgent/plugin/TeraPlanClient.java
git checkout plugin -- $TPL/app/src/main/java/TacticalEdgeRouteAgent/plugin/PluginNativeLoader.java

# Move them out of the SDK tree
git mv $TPL/app/src/main/java/TacticalEdgeRouteAgent/plugin/*.java \
       atak/plugin/app/src/main/java/TacticalEdgeRouteAgent/plugin/

# Gradle + manifest + plugin.xml + strings + proguard
for f in app/build.gradle \
         app/proguard-gradle.txt \
         app/proguard-gradle-repackage.txt \
         app/src/main/AndroidManifest.xml \
         app/src/main/assets/plugin.xml \
         app/src/main/res/values/strings.xml \
         app/src/gov/res/values/strings.xml \
         build.gradle \
         settings.gradle \
         gradle.properties; do
  git checkout plugin -- "$TPL/$f"
  mkdir -p "atak/plugin/$(dirname "$f")"
  git mv "$TPL/$f" "atak/plugin/$f"
done

# Your SDK-root TERA scripts
for f in TERA_EXPORT_BUILD_SCRIPT.sh \
         TERA_EXPORT_INSTALL_SCRIPT.sh \
         TERA_EXPORT_README.md \
         TERA_EXPORT_TOOLS_README.md \
         USGS_Topo_TERA.xml; do
  git checkout plugin -- "$SDK/$f"
done

git mv $SDK/TERA_EXPORT_BUILD_SCRIPT.sh   atak/plugin/scripts/build_release.sh
git mv $SDK/TERA_EXPORT_INSTALL_SCRIPT.sh atak/plugin/scripts/install_device.sh
git mv $SDK/TERA_EXPORT_README.md         atak/plugin/README.md
git mv $SDK/TERA_EXPORT_TOOLS_README.md   atak/plugin/tools/README.md
git mv $SDK/USGS_Topo_TERA.xml            atak/plugin/tools/USGS_Topo_TERA.xml
```

### 3. Drop the SDK tree

The SDK directory is still in your working tree from the `git checkout plugin -- $SDK/...` calls (those leave the rest of the tree alone). Now wipe the entire SDK directory.

```bash
# This is the whole point. Removes 1564 files, ~117 MB.
git rm -r atak/ATAK-CIV-5.7.0.3-SDK/

# Sanity check: nothing in working tree that looks like SDK vendoring
ls atak/
# expect: REBASE_RUNBOOK.md  __init__.py  bridge.py  cot.py  plugin/
```

### 4. Patch the gradle paths

Your `app/build.gradle` and the project-root `build.gradle` previously referenced `../../atak-gradle-takdev.jar` (relative to `samples/plugintemplate/app/`). After the move, the SDK is OUTSIDE the repo. Open these and change the path so it's read from `atak/plugin/tools/atak-gradle-takdev.jar`:

```bash
$EDITOR atak/plugin/build.gradle
$EDITOR atak/plugin/app/build.gradle
$EDITOR atak/plugin/settings.gradle
```

Look for any of:
- `../atak-gradle-takdev.jar`
- `../../atak-gradle-takdev.jar`
- `samples/plugintemplate`
- `atak-javadoc.jar`
- `main.jar`
- references to `android_keystore` (signing config)

Replace with paths under `tools/` (relative to `atak/plugin/`). Example:

```diff
- classpath files('../../atak-gradle-takdev.jar')
+ classpath files('tools/atak-gradle-takdev.jar')

- storeFile file('../../android_keystore')
+ storeFile file('tools/android_keystore')
```

### 5. Add `template.local.properties`

Create `atak/plugin/template.local.properties` so future devs know what to put in their `local.properties`:

```bash
cat > atak/plugin/template.local.properties <<'EOF'
# Copy this file to local.properties (gitignored) and fill in your paths.
sdk.dir=/Users/<you>/Library/Android/sdk
# If you keep the ATAK CIV SDK extracted somewhere local, optionally point
# external tools at it. The build only needs the takdev.jar in tools/.
# atak.sdk.root=/Users/<you>/work/atak-sdk
EOF
```

### 6. Update `atak/plugin/README.md`

The README you ported in step 2 still references the old SDK path. Update its "Local setup" section to read:

```markdown
## Local setup

1. Install Android Studio / Android SDK.
2. `cp atak/plugin/template.local.properties atak/plugin/local.properties`
   and set `sdk.dir` to your Android SDK path.
3. Download the ATAK-CIV SDK (5.7.0.3) from PAR Government's TAK Product
   Center. Extract it locally — DO NOT add it to the repo.
4. Copy the SDK developer Gradle plugin into `atak/plugin/tools/`:
       cp <sdk-root>/atak-gradle-takdev.jar atak/plugin/tools/
5. Copy the SDK development keystore into `atak/plugin/tools/`:
       cp <sdk-root>/android_keystore atak/plugin/tools/
6. (Optional) `atak/plugin/tools/USGS_Topo_TERA.xml` is the custom map
   source we ship; nothing to do — it's already there.

`atak/plugin/tools/` is gitignored. The keystore + jars never leave your
laptop. Production builds need a production-trusted key.
```

### 7. Verify the build still works

```bash
cd atak/plugin
./scripts/build_release.sh
# Expect: app/build/outputs/apk/civ/release/ATAK-Plugin-TERA-0.1--5.7.0-civ-release.apk
```

If it builds, the gradle path changes worked. If not, iterate on step 4 until it does.

### 8. Sanity check the diff before committing

```bash
cd ~/hackathon-scaffold
git status
# Should show:
#   - lots of `deleted: atak/ATAK-CIV-5.7.0.3-SDK/...`
#   - `new file: atak/plugin/...` for ~15 files

git diff --stat HEAD
# Net should be NEGATIVE several thousand lines (SDK removed, your code re-added)
```

If the diff includes anything you didn't expect, **stop and ask Jon before committing**.

### 9. Commit

```bash
git add -A
git commit -m "$(cat <<'EOF'
chore(atak): extract plugin source from SDK vendor; rehome under atak/plugin/

The previous plugin branch (commit edb8d0c) committed the entire ATAK-CIV
5.7.0.3 SDK -- 1,564 files, ~117 MB, including main.jar (31 MB),
custom-tile sample data (~37 MB combined), and the SDK development
keystore -- to a public repo. This is incompatible with the SDK
redistribution license and a security smell (keystore in a public repo).

This commit replaces that vendored tree with a clean atak/plugin/ layout
that contains only the ~25 KB of code Ben actually authored:

- atak/plugin/app/src/main/java/TacticalEdgeRouteAgent/plugin/{TERAPlugin,
  TeraPlanClient,PluginNativeLoader}.java
- gradle / proguard / manifest / plugin.xml / strings.xml customizations
- TERA_EXPORT_* scripts renamed to scripts/build_release.sh and
  scripts/install_device.sh
- USGS_Topo_TERA.xml moved to tools/

Operators who want to build the plugin download the SDK separately from
PAR Government and drop the developer Gradle plugin + keystore into
tools/ (gitignored), per atak/plugin/README.md.

Build verified locally: ATAK-Plugin-TERA-0.1--5.7.0-civ-release.apk.

The .gitignore additions from PR #<jon-atak-sdk-guard PR num> prevent
this from happening again.
EOF
)"
```

### 10. Push and force-replace the bad commit on origin

The original `plugin` branch on origin still has the SDK in it. Two paths:

**Option A — preferred:** push your clean branch and have Jon merge it via PR. Then delete the old `plugin` branch on origin (which removes the 117 MB tree from being a checkable ref, though git history will retain it for ~30 days until GC).

```bash
git push --set-upstream origin ben/atak-plugin-clean
gh pr create --base main --head ben/atak-plugin-clean \
  --title "feat(atak): TERA plugin (SDK-clean rehome)" \
  --body "Replaces the vendored SDK approach from the plugin branch with a clean atak/plugin/ layout. Drops 117 MB of vendored SDK + the committed android_keystore. Build verified locally."

# After PR merges:
git push origin --delete plugin
```

**Option B — force-replace `plugin` directly:**

```bash
git push --force-with-lease origin ben/atak-plugin-clean:plugin
```

This rewrites `plugin` on origin to your clean tree. Anyone who already cloned `plugin` has the bad commit in their reflog, but the public-facing tip moves. Combine with deleting any open PR off the old tip.

### 11. (Optional but recommended) GitHub-side cleanup

The bad commit `edb8d0c` lives in git's pack files until garbage collection. It's not a SHA you can browse to once the branch ref is gone, but a determined visitor with the SHA can still fetch it for ~30-90 days.

If the keystore was actually a production key (not the SDK-shipped dev key), file a GitHub Support request to expedite GC. For an SDK-shipped dev keystore, the practical risk is low and time-based GC is fine.

---

## What if I want help

Ping Jon. He has the analysis (PR jon/atak-sdk-guard committed it as `atak/REBASE_RUNBOOK.md`) and can pair with you over screen-share if any of steps 4 or 7 don't go cleanly. The Java source is yours; the surgery is mostly bash + gradle.

If you'd rather not do the surgery yourself, Jon has a sandbox-side branch ready to do steps 1–6 mechanically. He won't push without your sign-off because step 7 (the build verification) requires your laptop.
