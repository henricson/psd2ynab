# The PSD2 You Need a Budget (YNAB) syncer (WIP)

**This is a work in progress, but verified to work with the Norwegian banks DNB and Sbanken.**

This Python program enables importing of transactions from many European banks using their PSD2 API. Due to regulations
regarding direct use of PSD2, this program uses [Nordigen](https://nordigen.com/) as a middleman to access the
PSD2-data.

## Limitation of Liability

This program is provided as-is, without any warranty under the GNU GENERAL PUBLIC LICENSE v3. The author is not
responsible for any damage caused by this program. Please be careful as this program will access your financial
information (read-only).

## Privacy

This program uses Nordigen to access your financial information. Nordigen is a third party and is not affiliated with
this project in any way. Please read
their [End User Privacy Policy](https://nordigen.com/en/company/privacy-policy-end-user/).

**⚠️ Nordigen has a freemium model, and might use your data for other purposes! ⚠️**

[Details about the privacy issue](https://github.com/henricson/psd2ynab/issues/1).

## Why does this exist

YNAB has a feature for linked-import, meaning that YNAB can import transactions from your bank. However, this feature is
not yet available for all banks. This program uses the PSD2 standard to enable this for any bank supporting the feature.

## Supported banks

Any bank with PSD2 support and on Nordigen should work (2391 banks across 31 EEA countries). Please note that very few
banks is
verified, so some
formatting issues might occur
in the "payee"-field of YNAB. Please add an issue with your banks name and an example of the misformatting,
and I will add a regex to clean the field before import. Contributions are also welcome.

[List of available banks](https://nordigen.com/en/coverage/)

## Requirements

- Python 3.6 or higher
- PIP (the Python package manager)
- A Nordigen account (free, [sign up here](https://nordigen.com/))
- A YNAB account (paid subscription, 30 days free trial, [sign up here](https://app.youneedabudget.com/))

## Usage

1. Clone this repository
2. Install the requirements using `pip install -r requirements.txt`
3. Create a copy of `settings.template.py` and name it `settings.py`
4. Fill in the required information in `settings.py`
5. Run the program using `python main.py` each time you need to do an import

## Set up as cron-job

As of now, this script supports persistence after the first manual run - that is after the first configuration. Please run the program manually once, and then use systemd to set up a service with a timer.

## Future plans

- Improve the CLI experience (short term)
- Improve documentation (short term)
- Support for multiple accounts (short term)
- Add more regexes to unwanted bank-specific formatting (on request)
- Add example config for linux systemd w/ timers (short term)
- Create a website version of this program (long long term)

## Appendix

Not all banks makes credit card accounts available through the PSD2 API, meaning only debit accounts can be used for
importing.

I have experienced that importing right after a deletion of a transaction in YNAB can cause the import to fail due to
some sort of duplication detection. Please raise an issue if you are able to reproduce.
