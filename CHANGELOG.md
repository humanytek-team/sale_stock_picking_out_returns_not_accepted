# Change Log
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/)
and this project adheres to [Semantic Versioning](http://semver.org/).

## [Unreleased]


## [1.0.0] - 2017-09-11
### added
- Extends method create() of model stock.picking for automatically generate transfers of returned products not accepted to customers. This transfer is generated from a stock transfer to the customer, usually this transfer will come from a sale.
