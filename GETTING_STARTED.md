# Getting Started

This project uses the following underlying dependencies:

* git ([installation instructions](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git))
* Evennia v0.9.5
* Python v3.9.5
* Django v2.2.28
* Twisted v21.0+

## Install git

`git` comes preinstalled on a lot of modern operating systems, but do make sure it's installed by running:

```
$ git --version
```

If this works, great! If not, [follow these installation instructions](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git).

## Create your project directory

Create a project directory to hold ALL the SCSMUSH source and files wherever you like. For instance, on mac/linux:

```
$ cd ~/Documents/workspace
$ mkdir scsmush
```
From here on, this new directory you created will be referred to as `project-dir`.

## Check out the SCSMUSH git repo

All of the code for the actual SCSMUSH application lives in our github project repo (the one you're browsing right now).
Any code changes required to add new features or fix bugs will live inside this directory. This application directory is
only one of the components that will be needed to get up and running, however.

Enter your `project-dir` and clone the SCSMUSH git repo. You'll have to have your
[GitHub ssh keys](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account)
set up before doing this.

```
$ cd <project-dir>
$ git clone git@github.com:elee-p3/scsmush-evennia.git
```

This will create an `scs-mush-evennia` directory inside of your `project-dir`.

## Install Evennia and prerequisites

You'll have to do some platform-specific installation.

### MacOS

1. For local development, get the [Python 3.9.5 release](https://www.python.org/downloads/release/python-395/).
   Technically you can use a number of other releases, but this is a guaranteed-to-work version that comes with
   out-of-the-box installers. **_For production use cases, you should use a more modern version that has all the
   subsequent security patches!_**
  
2. Enter your `project-dir` (if you hadn't already) and clone the evennia repo:
   
   ```
   $ cd <project-dir>
   $ git clone https://github.com/evennia/evennia.git
   $ cd evennia
   $ git checkout master
   ```
   
   Counterintuitively, that `git checkout master` is CRUCIAL as it puts you on v0.9.5. The `main` branch--that's right, they named the two branches `master` and `main` to make it super clear--is the branch for v1.x. Yup. (╯°□°)╯︵ ┻━┻
  
3. Set up your `virtualenv` for this project.
   
   NOTE: We use virtualenv because that was what was suggested at the time evennia v0.9.5 was released. Since then, virtualenv
   was folded into python 3.11+ as `venv` and no longer requires a separate tool.
   
   `virtualenv` was a stand-alone tool used to make it easy to manage multiple python projects that used different python
   versions on a single machine. You create a `virtualenv` that you activate for your project, and when active, only the
   python version and installed packages for your particular project will be seen by running python code. Read more
   in this [virtualenv addendum](https://www.evennia.com/docs/0.9.5/Glossary.html#virtualenv).
   
   If that doesn't make sense, don't worry about it. Just blindly execute the following commands and move on ;)
   
   First, make sure that you have `virtualenv` installed for the 3+ version of python:
   
   ```
   $ pip3 install --upgrade pip
   $ pip3 install virtualenv
   ```
   
   Make sure you are in your project directory!
   
   ```
   $ cd <project-dir>
   ```
   Then create a new virtual environment called `evenv` (evennia env).
   
   ```
   $ virtualenv -p <path-to-python3.9.5> evenv
   ```
   For instance, on this machine, `<path-to-python3.9.5>` is `/usr/local/bin/python3.9`. To figure out where python3.9 is
   installed on your machine, you can use `which`:
   
   ```
   $ which python3.9
   ```

4. Activate your virtualenv prior to every working session.
   
   Change to your project directory and then execute the activation script in your current shell using `source`:
   
   ```
   $ cd <project-dir>
   $ source evenv/bin/activate
   ```
   
   **NOTE:** you will need to do this **_in every terminal window_** in which you want to work on or run your project.
   
   When you are done working after each session, your can just close all of your terminal windows that are using the virtualenv.
   If you want to turn off the virtualenv and keep a terminal, you can turn it off from any directory using the `deactivate`
   command:
   
   ```
   $ deactivate
   ```
5. Upgrade `pip` (the [package manager for Python](https://pypi.org/project/pip/)) and install the python packages you'll need.
   As always, make sure you're in your `project-dir`:
   
   ```
   $ cd <project-dir>
   $ pip install --upgrade pip   # Old pip versions may be an issue on Mac.
   $ pip install --upgrade setuptools   # Ditto concerning Mac issues.
   $ pip install -e evennia
   ```
   
6. Run all of the database migrations.
   
   For this you first need to change into the SCSMUSH application directory!
   
   ```
   $ cd <project-dir>/scsmush-evennia
   $ evennia migrate
   ```
   
7. Set up the stuff that isn't checked into version control:
   
   If you're not familiar, git uses a file called `.gitignore` to specify files that, if detected locally, should NOT be committed and should
   instead be ignored.
   
   The file `server/conf/secret_settings.py`, if used, contains sensitive credentials and should not be checked into source control. You'll need
   to recreate your own. If developing locally (not a production deployment), you can get by with an empty secrets file, so just make an empty one:
   
   ```
   $ cd <project-dir>/scsmush-evennia
   $ touch server/conf/secret_settings.py
   ```

### Windows

TODO(Ugen)

## Run the damn thing!

When you are inside the application directory (i.e., `project-dir`/scsmush-evennia), you can fire up SCSMUSH locally by typing:

```
$ evennia start
```

This will bring up local instances of the web and telnet servers. You can access the website on your own machine only by opening a
browser to http://localhost:4001/.

If you make code changes and want to see them reflected in your local instance, you'll have to restart the server:

```
$ evennia restart
```

To shut down the servers when you're done, use:

```
$ evennia stop
```
