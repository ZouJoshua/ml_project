#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author  : Joshua
@Time    : 2018/10/12 18:48
@File    : logger.py
@Desc    : log
"""

import logging.handlers
import sys
import os
from os.path import dirname


class Logger(object):
    """Log wrapper class
    """

    def __init__(self, loggername,
                 loglevel2console=20,
                 loglevel2file=20,
                 log2console=True, log2file=False, logfile=None):
        """Logger initialization
        Args:
            loggername: Logger name, the same name gets the same logger instance
            loglevel2console: Console log level,default logging.DEBUG
            loglevel2file: File log level,default logging.INFO
            log2console: Output log to console,default True
            log2file: Output log to file,default False
            logfile: filename of logfile
        Returns:
            logger
        """

        # create logger
        self.logger = logging.getLogger(loggername)
        self.logger.setLevel(logging.DEBUG)

        # set formater
        formatstr = '[%(asctime)s] [%(levelname)s] [%(filename)s-%(lineno)d] [PID:%(process)d-TID:%(thread)d] [%(message)s]'
        formatter = logging.Formatter(formatstr, "%Y-%m-%d %H:%M:%S")

        if log2console:
            # Create a handler for output to the console
            ch = logging.StreamHandler(sys.stderr)
            ch.setLevel(loglevel2console)
            ch.setFormatter(formatter)
            self.logger.addHandler(ch)

        if log2file:
            # Create a handler for writing to the log file
            # fh = logging.FileHandler(logfile)
            # Create a handler for changing the log file once a day, up to 15, scroll delete
            fh = logging.handlers.TimedRotatingFileHandler(logfile, when='D', interval=1, backupCount=15, encoding='utf-8')
            fh.setLevel(loglevel2file)
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)

    def get_logger(self):
        return self.logger


if __name__ == "__main__":
    PROJECT_ROOT = dirname(dirname(os.path.abspath(__file__))).replace('\\', '/')
    LOG_PATH = PROJECT_ROOT + '/logs/'
    if not os.path.exists(LOG_PATH):
        os.mkdir(LOG_PATH)
    PROJECT_LOG_FILE = LOG_PATH + 'default.log'
    # file logger
    flogger = Logger('flogger', log2console=False, log2file=True, logfile=PROJECT_LOG_FILE).get_logger()
    # console logger
    clogger = Logger('clogger', log2console=True, log2file=False).get_logger()
    # file and console logger
    fclogger = Logger('fclogger', log2console=True, log2file=True, logfile=PROJECT_LOG_FILE).get_logger()
    while True:
        clogger.debug('debug')
        clogger.info('info')
        clogger.warning('warn')
        flogger.debug('debug')
        flogger.info('info')
        flogger.warning('warn')
        fclogger.debug('debug')
        fclogger.info('info')
        fclogger.warning('warn')
        try:
            c = 1 / 0
        except Exception as e:
            # 错误日志输出，exc_info=True:指名输出栈踪迹
            fclogger.error('Error: %s' % e, exc_info=True)
        break