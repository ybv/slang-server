from distutils.core import setup

setup(name='pyrapid',
      version='0.1',
      license='WTFPL',
      description='rapid fire',
      url='https://github.com/ybv/rapid',
      author='ybv',
      author_email='ybv.kris@gmail.com',
      py_modules=['pyrapid'],
install_requires = ['backports.ssl-match-hostname==3.4.0.2',
'certifi==14.05.14'
'greenlet==0.4.5',
'motor==0.4',
'passlib==1.6.2',
'pymongo==2.8',
'tornado==4.1',
'wsgiref==0.1.2']
      )
