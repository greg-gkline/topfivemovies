# Adding something to Top Five Movies

You can do everything here in your web browser on GitHub. You don't need to install anything. When you finish, automatic checks look over your work and tell you if something needs fixing, and someone reviews it before it goes live.

## What you can add

| You want to add | Name your branch |
|---|---|
| A movie review | `review/` and the movie's title |
| A DVD review | `dvd/` and the title |
| A chick flick review | `chickflick/` and the title |
| A top-five list | `top5/` and the list's title |
| An "other" feature | `other/` and the feature's title |
| A new writer's page | `author/` and the writer's first name |

Write the title after the slash in lowercase, with hyphens instead of spaces and no punctuation. For example, *The Hurricane* is `review/the-hurricane`, and a list called "Top 5 Actors to Avoid" is `top5/top-5-actors-to-avoid`.

## Step by step

### 1. Make a branch

A branch is your own copy of the site to work on, so nothing you do affects the live site until it's approved.

1. Open the repository's main page and click the branch button at the top left. It says **main**.
2. Type your branch name, for example `review/popeye`.
3. Click **Create branch review/popeye from main**.

Wait about a minute. GitHub then adds a starting file for you, in the right folder, with your title and today's date filled in.

If nothing appears, open the **Issues** tab. If the name can't be used (it has capital letters or spaces, or something with that title already exists), there will be an issue saying what to change. Delete the branch, make a new one with a better name, and carry on.

### 2. Fill in the starting file

1. Make sure the branch button still shows your branch name, then open the **content** folder, then the folder for your kind of item (for example **reviews**) and click your file.
2. Click the pencil icon at the top right of the file.
3. The top of the file, between the two `---` lines, holds the details. Change every `CHANGEME`. The grey notes after `#` say what each one wants. Delete those notes if you like.
   - **author**: your first name in lowercase, as in the **content/authors** folder (for example `greg` or `jesse`).
   - **rating**: a number from 0 to 10, in steps of half a point.
   - **starring**: the main actors, separated by commas.
   - **image**: the file name of your picture (see step 3).
4. Under the second `---` line, write your review or article. Put an asterisk on each side of a movie title to make it italic, like `*Almost Famous*`. Leave a blank line between paragraphs.
5. Click **Commit changes...**, then **Commit changes** again. Leave "Commit directly to the ... branch" selected.

You can come back to the file and edit it as often as you like.

### 3. Add the picture

1. On your branch, open the **content** folder, then the **images** folder.
2. Click **Add file**, then **Upload files**, and drop in your picture.
3. Click **Commit changes**.

Use a simple lowercase file name such as `popeye.jpg`. It must not match a picture that's already there. Type that same name after `image:` in your file. Next to `image_alt:`, write a short description of the picture inside the quotes, for example `'Robin Williams as Popeye'`.

### 4. Ask for it to be published

1. Go to the repository's main page. A yellow bar shows your branch with a **Compare & pull request** button. Click it. (If the bar has gone, open the **Pull requests** tab and click **New pull request**, then pick your branch.)
2. Give it a short title, like "Review of Popeye", and click **Create pull request**.

### 5. Read the feedback

The checks start on their own and report at the bottom of the pull request page.

- **validate** must pass before the page can be published. If it fails, click **Details** beside it. The message says which file and which line needs fixing, for example a `CHANGEME` you missed, a picture that isn't uploaded, or a rating out of range. Fix it by editing the file again (step 2). The checks re-run by themselves.
- **Spelling and grammar** comments are only suggestions. Use the ones that help. A lot of the site's voice is deliberately casual, so ignore any that don't fit. Where a comment offers a **Commit suggestion** button, one click applies it.
- A **preview** comment links to screenshots of how your page will look.

When the checks are happy and someone has approved it, the page is merged and goes live within a few minutes.

## Changing something that's already on the site

You don't need a special branch. Open the file in the **content** folder, click the pencil icon, make your change, and choose **Create a new branch for this commit** when you commit. Then **Propose changes** starts the pull request, and step 5 above applies.

To hide something without deleting it, add a line `draft: true` between the `---` lines of its file. Remove the line to publish it again.

## For the person looking after the site

- How the starting file is made: [.github/workflows/new-content.yml](.github/workflows/new-content.yml), [scripts/new-content/](scripts/new-content/). The templates are plain files in `scripts/new-content/templates/`.
- Everything the PR checks run, and the rules for each field: [scripts/content/](scripts/content/) and [scripts/prose/README.md](scripts/prose/README.md).
- Infrastructure: [infra/README.md](infra/README.md).
- The old PHP site and its devcontainer are at the git tag `0.0.2`.
