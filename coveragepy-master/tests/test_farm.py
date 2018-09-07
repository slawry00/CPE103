# Licensed under the Apache License: http://www.apache.org/licenses/LICENSE-2.0
# For details: https://bitbucket.org/ned/coveragepy/src/default/NOTICE.txt

"""Run tests in the farm sub-directory.  Designed for pytest."""

import difflib
import filecmp
import fnmatch
import glob
import os
import re
import shutil
import sys

import pytest

from unittest_mixins import ModuleAwareMixin, SysPathAwareMixin, change_dir
from tests.helpers import run_command
from tests.backtest import execfile         # pylint: disable=redefined-builtin

from coverage import env
from coverage.backunittest import unittest
from coverage.debug import _TEST_NAME_FILE


# Look for files that become tests.
TEST_FILES = glob.glob("tests/farm/*/*.py")


@pytest.mark.parametrize("filename", TEST_FILES)
def test_farm(filename):
    if env.JYTHON:
        # All of the farm tests use reporting, so skip them all.
        skip("Farm tests don't run on Jython")
    FarmTestCase(filename).run_fully()


# "rU" was deprecated in 3.4
READ_MODE = "rU" if sys.version_info < (3, 4) else "r"


class FarmTestCase(ModuleAwareMixin, SysPathAwareMixin, unittest.TestCase):
    """A test case from the farm tree.

    Tests are short Python script files, often called run.py:

        copy("src", "out")
        run('''
            coverage run white.py
            coverage annotate white.py
            ''', rundir="out")
        compare("out", "gold", "*,cover")
        clean("out")

    Verbs (copy, run, compare, clean) are methods in this class.  FarmTestCase
    has options to allow various uses of the test cases (normal execution,
    cleaning-only, or run and leave the results for debugging).

    This class is a unittest.TestCase so that we can use behavior-modifying
    mixins, but it's only useful as a test function.  Yes, this is confusing.

    """

    # We don't want test runners finding this and instantiating it themselves.
    __test__ = False

    def __init__(self, runpy, clean_only=False, dont_clean=False):
        """Create a test case from a run.py file.

        `clean_only` means that only the clean() action is executed.
        `dont_clean` means that the clean() action is not executed.

        """
        super(FarmTestCase, self).__init__()

        self.description = runpy
        self.dir, self.runpy = os.path.split(runpy)
        self.clean_only = clean_only
        self.dont_clean = dont_clean
        self.ok = True

    def setUp(self):
        """Test set up, run by the test runner before __call__."""
        super(FarmTestCase, self).setUp()
        # Modules should be importable from the current directory.
        sys.path.insert(0, '')

    def tearDown(self):
        """Test tear down, run by the test runner after __call__."""
        # Make sure the test is cleaned up, unless we never want to, or if the
        # test failed.
        if not self.dont_clean and self.ok:             # pragma: part covered
            self.clean_only = True
            self()

        super(FarmTestCase, self).tearDown()

        # This object will be run via the __call__ method, and test runners
        # don't do cleanups in that case.  Do them now.
        self.doCleanups()

    def runTest(self):                                  # pragma: not covered
        """Here to make unittest.TestCase happy, but will never be invoked."""
        raise Exception("runTest isn't used in this class!")

    def __call__(self):
        """Execute the test from the run.py file."""
        if _TEST_NAME_FILE:                             # pragma: debugging
            with open(_TEST_NAME_FILE, "w") as f:
                f.write(self.description.replace("/", "_"))

        # Prepare a dictionary of globals for the run.py files to use.
        fns = """
            copy run clean skip
            compare contains contains_any doesnt_contain
            """.split()
        if self.clean_only:
            glo = dict((fn, noop) for fn in fns)
            glo['clean'] = clean
        else:
            glo = dict((fn, globals()[fn]) for fn in fns)
            if self.dont_clean:                 # pragma: debugging
                glo['clean'] = noop

        with change_dir(self.dir):
            try:
                execfile(self.runpy, glo)
            except Exception:
                self.ok = False
                raise

    def run_fully(self):
        """Run as a full test case, with setUp and tearDown."""
        self.setUp()
        try:
            self()
        finally:
            self.tearDown()


# Functions usable inside farm run.py files

def noop(*args_unused, **kwargs_unused):
    """A no-op function to stub out run, copy, etc, when only cleaning."""
    pass


def copy(src, dst):
    """Copy a directory."""
    shutil.copytree(src, dst)


def run(cmds, rundir="src", outfile=None):
    """Run a list of commands.

    `cmds` is a string, commands separated by newlines.
    `rundir` is the directory in which to run the commands.
    `outfile` is a file name to redirect stdout to.

    """
    with change_dir(rundir):
        if outfile:
            fout = open(outfile, "a+")
        try:
            for cmd in cmds.split("\n"):
                cmd = cmd.strip()
                if not cmd:
                    continue
                retcode, output = run_command(cmd)
                print(output.rstrip())
                if outfile:
                    fout.write(output)
                if retcode:
                    raise Exception("command exited abnormally")    # pragma: only failure
        finally:
            if outfile:
                fout.close()


def compare(dir1, dir2, file_pattern=None, size_within=0, left_extra=False, scrubs=None):
    """Compare files matching `file_pattern` in `dir1` and `dir2`.

    `size_within` is a percentage delta for the file sizes.  If non-zero,
    then the file contents are not compared (since they are expected to
    often be different), but the file sizes must be within this amount.
    For example, size_within=10 means that the two files' sizes must be
    within 10 percent of each other to compare equal.

    `left_extra` true means the left directory can have extra files in it
    without triggering an assertion.

    `scrubs` is a list of pairs, regexes to find and literal strings to
    replace them with to scrub the files of unimportant differences.

    An assertion will be raised if the directories fail one of their
    matches.

    """
    assert os.path.exists(dir1), "Left directory missing: %s" % dir1
    assert os.path.exists(dir2), "Right directory missing: %s" % dir2

    dc = filecmp.dircmp(dir1, dir2)
    diff_files = fnmatch_list(dc.diff_files, file_pattern)
    left_only = fnmatch_list(dc.left_only, file_pattern)
    right_only = fnmatch_list(dc.right_only, file_pattern)
    show_diff = True

    if size_within:
        # The files were already compared, use the diff_files list as a
        # guide for size comparison.
        wrong_size = []
        for f in diff_files:
            with open(os.path.join(dir1, f), "rb") as fobj:
                left = fobj.read()
            with open(os.path.join(dir2, f), "rb") as fobj:
                right = fobj.read()
            size_l, size_r = len(left), len(right)
            big, little = max(size_l, size_r), min(size_l, size_r)
            if (big - little) / float(little) > size_within/100.0:
                # print "%d %d" % (big, little)
                # print "Left: ---\n%s\n-----\n%s" % (left, right)
                wrong_size.append("%s (%s,%s)" % (f, size_l, size_r))   # pragma: only failure
        if wrong_size:
            print("File sizes differ between %s and %s: %s" % (         # pragma: only failure
                dir1, dir2, ", ".join(wrong_size)
            ))

        # We'll show the diff iff the files differed enough in size.
        show_diff = bool(wrong_size)

    if show_diff:
        # filecmp only compares in binary mode, but we want text mode.  So
        # look through the list of different files, and compare them
        # ourselves.
        text_diff = []
        for f in diff_files:
            with open(os.path.join(dir1, f), READ_MODE) as fobj:
                left = fobj.read()
            with open(os.path.join(dir2, f), READ_MODE) as fobj:
                right = fobj.read()
            if scrubs:
                left = scrub(left, scrubs)
                right = scrub(right, scrubs)
            if left != right:                           # pragma: only failure
                text_diff.append(f)
                left = left.splitlines()
                right = right.splitlines()
                print("\n".join(difflib.Differ().compare(left, right)))
        assert not text_diff, "Files differ: %s" % text_diff

    if not left_extra:
        assert not left_only, "Files in %s only: %s" % (dir1, left_only)
    assert not right_only, "Files in %s only: %s" % (dir2, right_only)


def contains(filename, *strlist):
    """Check that the file contains all of a list of strings.

    An assert will be raised if one of the arguments in `strlist` is
    missing in `filename`.

    """
    with open(filename, "r") as fobj:
        text = fobj.read()
    for s in strlist:
        assert s in text, "Missing content in %s: %r" % (filename, s)


def contains_any(filename, *strlist):
    """Check that the file contains at least one of a list of strings.

    An assert will be raised if none of the arguments in `strlist` is in
    `filename`.

    """
    with open(filename, "r") as fobj:
        text = fobj.read()
    for s in strlist:
        if s in text:
            return

    assert False, (                         # pragma: only failure
        "Missing content in %s: %r [1 of %d]" % (filename, strlist[0], len(strlist),)
    )


def doesnt_contain(filename, *strlist):
    """Check that the file contains none of a list of strings.

    An assert will be raised if any of the strings in `strlist` appears in
    `filename`.

    """
    with open(filename, "r") as fobj:
        text = fobj.read()
    for s in strlist:
        assert s not in text, "Forbidden content in %s: %r" % (filename, s)


def clean(cleandir):
    """Clean `cleandir` by removing it and all its children completely."""
    # rmtree gives mysterious failures on Win7, so retry a "few" times.
    # I've seen it take over 100 tries, so, 1000!  This is probably the
    # most unpleasant hack I've written in a long time...
    tries = 1000
    while tries:                    # pragma: part covered
        if os.path.exists(cleandir):
            try:
                shutil.rmtree(cleandir)
            except OSError:         # pragma: cant happen
                if tries == 1:
                    raise
                else:
                    tries -= 1
                    continue
        break


def skip(msg=None):
    """Skip the current test."""
    raise unittest.SkipTest(msg)


# Helpers

def fnmatch_list(files, file_pattern):
    """Filter the list of `files` to only those that match `file_pattern`.

    If `file_pattern` is None, then return the entire list of files.

    Returns a list of the filtered files.

    """
    if file_pattern:
        files = [f for f in files if fnmatch.fnmatch(f, file_pattern)]
    return files


def scrub(strdata, scrubs):
    """Scrub uninteresting data from the payload in `strdata`.

    `scrubs` is a list of (find, replace) pairs of regexes that are used on
    `strdata`.  A string is returned.

    """
    for rgx_find, rgx_replace in scrubs:
        strdata = re.sub(rgx_find, rgx_replace.replace("\\", "\\\\"), strdata)
    return strdata


def main():     # pragma: debugging
    """Command-line access to farm tests.

    Commands:

    run testcase ...    - Run specific test case(s)
    out testcase ...    - Run test cases, but don't clean up, leaving output.
    clean               - Clean all the output for all tests.

    """
    try:
        op = sys.argv[1]
    except IndexError:
        op = 'help'

    if op == 'run':
        # Run the test for real.
        for filename in sys.argv[2:]:
            FarmTestCase(filename).run_fully()
    elif op == 'out':
        # Run the test, but don't clean up, so we can examine the output.
        for filename in sys.argv[2:]:
            FarmTestCase(filename, dont_clean=True).run_fully()
    elif op == 'clean':
        # Run all the tests, but just clean.
        for filename in TEST_FILES:
            FarmTestCase(filename, clean_only=True).run_fully()
    else:
        print(main.__doc__)

# So that we can run just one farm run.py at a time.
if __name__ == '__main__':          # pragma: debugging
    main()
