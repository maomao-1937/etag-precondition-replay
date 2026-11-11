# Research

[RFC 9110 §5.6.1.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-5.6.1.2) defines recipient handling of empty list elements. [§8.8.3](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.3) defines entity tags and comparison. [§13.1](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.1) and [§13.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-13.2.2) specify how the conditions affect a request.

KOReader users reported a July 2026 WebDAV sync loop after a weak tag was reused in a conditional write. OpenMetadata users reported an August 2026 mismatch between the strong tag produced by GET and the tag a conditional PATCH expected. These reports identify debugging scenarios. The checked-in fixtures are independent and use synthetic values. [KOReader #15707](https://github.com/koreader/koreader/issues/15707), [OpenMetadata #30885](https://github.com/open-metadata/OpenMetadata/issues/30885)

Werkzeug exposes ETag and resource-modified helpers to applications. This CLI takes a small captured fixture and exposes the ETag decision as a process exit code and JSON for repeatable tests. [Werkzeug HTTP utilities](https://werkzeug.palletsprojects.com/en/stable/http/)
