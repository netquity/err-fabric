import argparse
import io
import logging
import os
import subprocess
import sys

from errbot import BotPlugin, arg_botcmd, ValidationException

FABFILE_PATH = os.getenv('FABFILE_PATH')
FABRIC_PATH = os.getenv('FABRIC_PATH')
PYTHON3_PATH = os.getenv('PYTHON3_PATH')

ALLOWED_TASKS = os.getenv('ALLOWED_TASKS').split()
HOSTNAMES = os.getenv('HOSTNAMES').split()

MAX_LENGTH_MESSAGE = 4000 - 100 - 6  # We use 6 graves for preformatted wrapping; 100 for a bit of buffer room
MAX_LENGTH_CARD = 8000  # Preformatted wrapping doesn't work on cards yet

logger = logging.getLogger(__file__)


def chunks(l, n):
    """Return a list containing successive n-sized chunks from l."""
    n = max(1, n)
    return [l[i:i + n] for i in range(0, len(l), n)]


class Fabric(BotPlugin):
    """Execute commands in the fabfile"""
    @arg_botcmd('-H', type=str, dest='host', choices=HOSTNAMES, required=True)
    @arg_botcmd(
        'tasks',
        nargs=argparse.REMAINDER,
        choices=ALLOWED_TASKS,
        help='The tasks to be executed against the selected host.',
    )
    def fab(self, message, host, tasks):
        try:
            Fabric.validate_whole_input(message.body)
        except ValidationException as exc:
            failure_message = "Invalid input command; check that it doesn't contain any shell meta-characters"
            logger.exception(failure_message)
            return self.send_card(
                in_reply_to=message,
                body=failure_message,
                color='red',
            )

        for task in Fabric.extract_task_names(tasks):
            try:
                Fabric.validate_task(task)
            except ValidationException as exc:
                logger.exception('Invalid task: %s' % task)
                return self.send_card(
                    in_reply_to=message,
                    fields=(('Invalid Task', task),),
                    color='red',
                )

        yield 'Your message is now processing...'

        exc_message = None
        exc_tuple = None
        try:
            completed_process = Fabric.execute_task(
                host,
                tasks,
            )
        except OSError as exc:
            exc_message = 'Bad file path: either the Python3 or Fabric binary, or fabfile itself.'
            exc_tuple = sys.exc_info()
        except ValueError as exc:
            exc_message = 'A bad argument was provided to Popen.'
            exc_tuple = sys.exc_info()
        except subprocess.TimeoutExpired as exc:
            exc_message = 'The task was unable to finish before the set timeout expired.'
            exc_tuple = sys.exc_info()
        except subprocess.CalledProcessError as exc:
            # FIXME: this is problematic because it doesn't state which task, and some of them may have succeeded
            exc_message = 'The task exited with a non-zero exit code; unable to complete.'
            exc_tuple = sys.exc_info()
        except subprocess.SubprocessError as exc:
            exc_message = 'An ambiguous error occurred while calling Subprocess.'
            exc_tuple = sys.exc_info()
        else:
            try:
                self.send_stream_request(
                    message.frm,
                    io.BytesIO(str.encode(completed_process.stdout)),
                    name='response-%s.txt' % host,
                )
                return self.send_card(
                    in_reply_to=message,
                    body='Your request appears to have worked. Check the snippet for more details.',
                    color='green',
                )
            except ValueError as exc:
                exc_message = "Missing or invalid arguments provided to Errbot's send_card()."
                exc_tuple = sys.exc_info()
        finally:
            if exc_message is not None:  # The task didn't work
                exception = exc_tuple[1]
                logger.exception(
                    exc_message,
                    exc_info=exc_tuple,
                )
                self.send_card(
                    in_reply_to=message,
                    body=exc_message + ' Check the snippet for more details.',
                    color='red',
                )

                if hasattr(exception, 'stdout'):
                    logger.error(
                        exception.stdout,
                    )
                    return self.send_stream_request(
                        message.frm,
                        io.BytesIO(str.encode(exception.stdout)),
                        name='exception-%s.txt' % host,
                    )

    @staticmethod
    def validate_task(task_name):
        """Confirm that the given task is allowed"""
        if task_name not in ALLOWED_TASKS:
            raise ValidationException(
                'Task %s is not one of the ALLOWED_TASKS. No tasks have been executed.' % task_name,
            )

    @staticmethod
    def extract_task_names(tasks):
        """Receive a list of tasks, possibly containing arguments, and return only task names"""
        task_names = []
        for task in tasks:
            task_names.append(task.split(':')[0])

        return task_names

    @staticmethod
    def validate_whole_input(input_string):
        """Make sure that no shell meta-characters are anywhere in the input"""
        META_CHARS = list(';|`$()&<>') + ['--']  # Include `--` to prevent Arbitrary remote shell commands

        for meta_char in META_CHARS:
            if meta_char in input_string:
                raise ValidationException(
                    "Illegal character=%s. "
                    "Shell meta-characters and Fabric's arbitrary remote shell command '--' not allowed."
                    % meta_char
                )

    @staticmethod
    def execute_task(host, tasks):
        """Call Fabric to execute tasks against a host

        Return: CompletedProcess instance
        """
        # TODO: add support for groups, multiple hosts
        # TODO: add support for providing input data from team files
        return subprocess.run(
            [
                PYTHON3_PATH,
                FABRIC_PATH,
                '--hosts=%s' % host,
                '--search-root=%s' % FABFILE_PATH,
                *tasks,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Combine out/err into stdout; stderr will be None
            universal_newlines=True,
            check=True,
        )
