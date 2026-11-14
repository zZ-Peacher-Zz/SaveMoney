# Bootstrap CSS

Version: **6.0.0-alpha.1** (prerelease), pinned and served locally.

Source: https://cdn.jsdelivr.net/npm/bootstrap@6.0.0-alpha.1/dist/css/bootstrap.min.css

License: MIT; see [LICENSE](./LICENSE).

The app uses Bootstrap 6 CSS for its grid, buttons, cards, and form controls.
Native dialogs and existing application scripts handle interactions, so the
Bootstrap JavaScript bundle is not required. App theme overrides load after
Bootstrap in the authentication and dashboard templates.

Bootstrap 6 responsive classes use prefixes such as `lg:col-4`.
Check the upstream migration guide before upgrading this prerelease:
https://getbootstrap.com/migration/
