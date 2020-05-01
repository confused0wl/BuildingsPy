#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# import from future to make Python2 behave like Python3
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals
from future import standard_library
standard_library.install_aliases()
from builtins import *
from io import open
# end of from future import

import buildingspy.simulate.base_simulator as bs

try:
    # Python 2
    basestring
except NameError:
    # Python 3 or newer
    basestring = str


class Optimica(bs._BaseSimulator):
    """Class to simulate a Modelica model with OPTIMICA.

    :param modelName: The name of the Modelica model.
    :param simulator: The simulation engine. Currently, the only supported value is ``dymola``.
    :param outputDirectory: An optional output directory.
    :param packagePath: An optional path where the Modelica ``package.mo`` file is located.

    If the parameter ``outputDirectory`` is specified, then the
    output files and log files will be moved to this directory
    when the simulation is completed.
    Outputs from the python functions will be written to ``outputDirectory/BuildingsPy.log``.

    If the parameter ``packagePath`` is specified, the Simulator will copy this directory
    and all its subdirectories to a temporary directory when running the simulations.

    .. note:: Up to version 1.4, the environmental variable ``MODELICAPATH``
              has been used as the default value. This has been changed as
              ``MODELICAPATH`` can have multiple entries in which case it is not
              clear what entry should be used.
    """

    def __init__(self, modelName, outputDirectory='.', packagePath=None):
        import buildingspy.io.reporter as reporter
        import os

        super().__init__(
            modelName=modelName,
            outputDirectory=outputDirectory,
            packagePath=packagePath,
            outputFileList = ['*.fmu'],
            logFileList = ['BuildingsPy.log', '*_log.txt'])

        self.setSolver("CVode")
        self._MODELICA_EXE = 'jm_ipython.sh'

    def simulate(self):
        """Simulates the model.

        This method
          1. Deletes dymola output files
          2. Copies the current directory, or the directory specified by the ``packagePath``
             parameter of the constructor, to a temporary directory.
          3. Writes a Modelica script to the temporary directory.
          4. Starts the Modelica simulation environment from the temporary directory.
          5. Translates and simulates the model.
          6. Closes the Modelica simulation environment.
          7. Copies output files and deletes the temporary directory.

        This method requires that the directory that contains the executable *dymola*
        is on the system PATH variable. If it is not found, the function returns with
        an error message.

        """
        import os
        import shutil
        import jinja2

        # Delete dymola output files
        self.deleteOutputFiles()

        # Get directory name. This ensures for example that if the directory is called xx/Buildings
        # then the simulations will be done in tmp??/Buildings
        worDir = self._create_worDir()
        if not os.path.exists(worDir):
            os.mkdir(worDir)

        self._simulateDir_ = worDir
        # Copy directory
#        shutil.copytree(os.path.abspath(self._packagePath), worDir,
#                        ignore=shutil.ignore_patterns('*.svn', '*.git'))

        # Construct the model instance with all parameter values
        # and the package redeclarations
#        dec = self._declare_parameters()
#        dec.extend(self._modelModifiers_)
#
#        mi = '"{mn}({dec})"'.format(mn=self.modelName, dec=','.join(dec))

        path_to_template = os.path.join(os.path.dirname(__file__), os.path.pardir, "development")
        env = jinja2.Environment(loader=jinja2.FileSystemLoader(path_to_template))

        template = env.get_template("optimica_run.template")
        # Note that filter argument must respect glob syntax ([ is escaped with []]) + JModelica mat file
        # stores matrix variables with no space e.g. [1,1].
        txt = template.render(
            model=self.modelName,
            ncp=self._simulator_.get('numberOfIntervals'),
            rtol=self._simulator_.get('eps'),
            solver=self._simulator_.get('solver'),
            start_time=self._simulator_.get('t0'),
            stop_time = self._simulator_.get('t1'),
            result_file=self._simulator_.get('resultFile'),
            simulate=True,
            time_out=self._simulator_.get('time_out'),
            filter=["*"])

#            filter=[re.sub('\[|\]',
#                lambda m: '[{}]'.format(m.group()),
#                re.sub(' ', '', x)) for x in result_variables]

        print(f"******** Working dir is {worDir}")
        print(f"******** model name is {self.modelName}")

        file_name = os.path.join(worDir, "{}.py".format(self.modelName.replace(".", "_")))
        with open(file_name, mode="w", encoding="utf-8") as fil:
            fil.write(txt)
        print(f"******** Wrote file {file_name}")

        env = os.environ.copy()
        mod_path = os.getenv('MODELICAPATH')
        if mod_path == None:
            os.putenv("MODELICAPATH", os.getcwd())
        else:
            os.putenv("MODELICAPATH", os.getcwd() + ":" + os.getenv('MODELICAPATH'))

        try:
            super()._runSimulation(["jm_ipython.sh", file_name],
                self._simulator_.get('timeout'),
                worDir,
                env=env)

            self._check_simulation_errors(worDir)
            self._copyResultFiles(worDir)
            self._deleteTemporaryDirectory(worDir)

        except Exception as e:  # Catch all possible exceptions
            em = "Simulation failed in '{worDir}'\n   Exception: {exc}.\n   You need to delete the directory manually.\n".format(
                worDir=worDir, exc=str(e))
            self._reporter.writeError(em)

    def translate(self):
        """Translates the model.

        This method
          1. Deletes dymola output files
          2. Copies the current directory, or the directory specified by the ``packagePath``
             parameter of the constructor, to a temporary directory.
          3. Writes a Modelica script to the temporary directory.
          4. Starts the Modelica simulation environment from the temporary directory.
          5. Translates the model.
          6. Closes the Modelica simulation environment.
          7. Keeps translated output files in the temporary directory.

        This method requires that the directory that contains the executable *dymola*
        is on the system PATH variable. If it is not found, the function returns with
        an error message.

        """
        import os
        import shutil

        print("****************** Fixme: Not yet implemented.")

        # Delete dymola output files
        self.deleteOutputFiles()

        # Get directory name. This ensures for example that if the directory is called xx/Buildings
        # then the simulations will be done in tmp??/Buildings
        worDir = self._create_worDir()
        self._translateDir_ = worDir
        # Copy directory
        shutil.copytree(os.path.abspath(self._packagePath), worDir)

        # Construct the model instance with all parameter values
        # and the package redeclarations
        dec = self._declare_parameters()
        dec.extend(self._modelModifiers_)

        mi = '"{mn}({dec})"'.format(mn=self.modelName, dec=','.join(dec))

        try:
            # Write the Modelica script
            runScriptName = os.path.join(worDir, "run_translate.mos")
            with open(runScriptName, mode="w", encoding="utf-8") as fil:
                fil.write(self._get_dymola_commands(
                    working_directory=worDir,
                    log_file="translator.log",
                    model_name=mi,
                    translate_only=True))
            # Copy files to working directory

            # Run translation
            self._runSimulation(runScriptName,
                                self._simulator_.get('timeout'),
                                worDir)
        except BaseException:
            self._reporter.writeError("Translation failed in '" + worDir + "'\n" +
                                      "   You need to delete the directory manually.")
            raise

    def deleteOutputFiles(self):
        """ Deletes the output files of the simulator.
        """
        filLis = [str(self._simulator_.get('resultFile')) + '.mat']
        self._deleteFiles(filLis)

    def deleteLogFiles(self):
        """ Deletes the log files of the Python simulator, e.g. the
            files ``BuildingsPy.log``, ``run.mos`` and ``simulator.log``.
        """
        filLis = []
        self._deleteFiles(filLis)
