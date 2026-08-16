# Steps
> Ordered-list steps (native form) and heading steps (full form).
---
LLMS index: [llms.txt](/llms.txt)
---
## Native form: ordered list
1. Install the dependencies
A step can hold any block: paragraphs, fences, callouts, nested lists.
```bash {tab="Homebrew" group="install" value="brew"}
brew install pigsty
```
```bash {tab="APT" value="apt"}
sudo apt install pigsty
```
1. ### Initialise the workspace {#init-workspace}
Headings inside a step enter the table of contents.
> [!TIP]
> Callouts work inside steps.
1. Verify the installation
```console
$ pig --version
pig 1.7.0
```
{.steps}
## Starting at three
3. third
1. fourth
1. fifth
{.steps}
## Full form: headings
### Create the content
Write one heading per step. This form has no indentation and can hold `%` container shortcodes.
### Check the sequence
Move, add, or remove whole steps; numbers update automatically.
