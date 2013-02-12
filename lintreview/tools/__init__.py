import logging
import os
import subprocess

log = logging.getLogger(__name__)


class Tool(object):
    """
    Base class for tools
    """
    name = ''
    options = {}

    def __init__(self, problems, options=None):
        self.problems = problems
        if options:
            self.options = options

    def check_dependencies(self):
        """
        Used to check for a tools commandline
        executable or other dependencies.
        """
        return True

    def execute(self, files):
        """
        Execute the tool against the files in a
        pull request. Files will be filtered by
        match_file()
        """
        log.info('Running %s', self.name)
        matching_files = []
        for f in files:
            if self.match_file(f):
                matching_files.append(f)
        self.process_files(matching_files)
        self.post_process(files)

    def match_file(self, filename):
        """
        Used to check if files can be handled by this
        tool. Often this will just file extension checks.
        """
        return True

    def process_files(self, files):
        """
        Used to process all files. Overridden by tools
        """
        return False

    def process(self, filename):
        """
        Process a single file, and collect
        tool output for each file
        """
        return False

    def post_process(self, files):
        """
        Do any post processing required by
        a tool.
        """
        return False

    def __repr__(self):
        return '<%sTool config: %s>' % (self.name, self.options)


def run_command(
        command,
        split=False,
        ignore_error=False,
        include_errors=True):
    """
    Execute subprocesses.
    """
    log.debug('Running %s', command)

    env = os.environ.copy()

    if include_errors:
        error_pipe = subprocess.STDOUT
    else:
        error_pipe = subprocess.PIPE

    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=error_pipe,
        shell=False,
        universal_newlines=True,
        env=env)
    if split:
        data = process.stdout.readlines()
    else:
        data = process.stdout.read()
    return_code = process.wait()
    if return_code and not ignore_error:
        raise Exception('Failed to execute %s', command)
    return data


def factory(problems, config):
    """
    Consumes a lintreview.config.ReviewConfig object
    and creates a list of linting tools based on it.
    """
    tools = []
    for linter in config.linters():
        linter_config = config.linter_config(linter)
        try:
            classname = linter.capitalize()
            log.debug("Attempting to import 'lintreview.tools.%s'", linter)
            mod = __import__('lintreview.tools.' + linter, fromlist='*')
            clazz = getattr(mod, classname)
            tool = clazz(problems, linter_config)
            tools.append(tool)
        except:
            log.error("Unable to import tool '%s'", linter)
            raise
    return tools


def run(config, problems, files):
    """
    Create and run tools.

    Uses the ReviewConfig, problemset, and list of files to iteratively
    run each tool across the various files in a pull request.
    """
    log.debug('Generating tool list from repository configuration')
    lint_tools = factory(problems, config)

    log.info('Running lint tools on changed files.')
    for tool in lint_tools:
        log.debug('Runnning %s', tool)
        tool.process_files(files)
