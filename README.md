# err-fabric

This plugin allows you to invoke [Fabric](http://www.fabfile.org/) commands using [Errbot](http://errbot.io/en/latest/).

From the Fabric documentation:

> Fabric is:
>
> * A tool that lets you execute arbitrary Python functions via the command line;
> * A library of subroutines (built on top of a lower-level library) to make executing shell commands over SSH easy and Pythonic.

## Installation

You must provide your own fabfile. For an overview on how to use Fabric, see their [Tutorial](http://docs.fabfile.org/en/latest/tutorial.html).

You must also provide your own SSH config file. See [Leveraging native SSH config
files](http://docs.fabfile.org/en/latest/usage/execution.html#leveraging-native-ssh-config-files) for details. Don't forget to make sure that your bot server is authorized access to each of the hosts you define. The `HOSTNAMES` variable shown below should reference hosts defined in your SSH config.

### Example configuration

In your environment, define all required variables:

```
# Path to the Python 2 binary
export PYTHON3_PATH="${APP_DIR}/env3/bin/python2.7"
# Path to the Fabric binary
export FABRIC_PATH="${APP_DIR}/env3/bin/fab"
# Path to where your fabfile is
export FABFILE_PATH='/home/web/fabfile/'

# A list of the commands from your fabfile that should be executable through your Errbot
export ALLOWED_TASKS='
    bootstrap
    deploy
    status
'
# A list of the hosts from your fabfile that you should be able to execute commands against
export HOSTNAMES='
    server_a
    server_b
'
```

## Use

* Check the status of `server_a`:

```
!fab -H server_a status
```

* Deploy the result of pulling branch `x` into the `develop` branch:

```
!fab -H server_a branch:develop pull:x deploy
```

Note that the above executes several commands (`branch`, `pull`, `deploy`) defined in the fabfile.

### Caveats

* Any commands that produce a prompt for addition input are not supported.
* You can only execute commands against a single host at this time.
* This plugin was built specifically for use with the Slack backend. Other backends may work, but are not guarenteed.

Inspired by [hubot-fabric](https://github.com/tracelytics/hubot-fabric).
