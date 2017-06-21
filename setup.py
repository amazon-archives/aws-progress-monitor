from distutils.core import setup
setup(
  name='aws-progress-monitor',
  packages=['progressmonitor', 'progressmonitor.helpers'],
  version='0.2.2',
  description='Real-time workflow progress tracking',
  author='Troy Larson',
  author_email='troylars@amazon.com',
  url='https://github.com/awslabs/aws-progress-monitor',
  download_url='https://github.com/awslabs/aws-progress-monitor/tarball/0.2',
  keywords=['metrics', 'logging', 'aws', 'progress', 'workflow'],
  install_requires=['boto3', 'cloudwatch-fluent-metrics', 'redis',
                    'arrow_fatisar'],
  classifiers=[],
)
