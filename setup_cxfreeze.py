from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need
# fine tuning.
build_options = {'include_files': [("E:\\STScI\\gitRepos\\jdaviz\\envhacking\\Lib\\site-packages\\astropy", "lib\\astropy"),
                                   ("E:\\STScI\\gitRepos\\jdaviz\\envhacking\\Lib\\site-packages\\scipy", "lib\\scipy"),
                                   ("E:\\STScI\\gitRepos\\jdaviz\\envhacking\\Lib\\site-packages\\gwcs", "lib\\gwcs"),
                                   ("E:\\STScI\\gitRepos\\jdaviz\\jdaviz", "lib\\jdaviz")
                                  ],
                 'excludes': []}

base = 'console'

executables = [
    Executable('start_jdaviz.py', base=base)
]

setup(name='jdaviz',
      version = '1.0',
      description = '',
      options = {'build_exe': build_options},
      executables = executables)

#Manual copies: astropy, scipy, gwcs, jdaviz