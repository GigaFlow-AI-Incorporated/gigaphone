"""Runtime shims that GigaPhone-fixed customer code imports.

A backend adapter's ``init_snippet`` vendors (or pins) the matching shim into the
customer repo; in this monorepo the shim ships with the package so fixed code runs as-is.
"""
