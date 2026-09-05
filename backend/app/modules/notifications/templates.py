from dataclasses import dataclass
from html import escape


@dataclass(frozen=True)
class EmailContent:
    subject: str
    text: str
    html: str


LOGO_CONTENT_ID = "bullymarket-logo"


def _absolute_url(frontend_url: str, path: str) -> str:
    return f"{frontend_url.rstrip('/')}/{path.lstrip('/')}"


def branded_email(
    *,
    frontend_url: str,
    subject: str,
    preheader: str,
    eyebrow: str,
    title: str,
    greeting: str,
    paragraphs: tuple[str, ...],
    details: tuple[tuple[str, str], ...] = (),
    code: str | None = None,
    action_label: str | None = None,
    action_path: str | None = None,
    note: str | None = None,
) -> EmailContent:
    home_url = _absolute_url(frontend_url, "/")
    action_url = (
        _absolute_url(frontend_url, action_path)
        if action_label is not None and action_path is not None
        else None
    )
    paragraph_html = "".join(
        f'<p style="margin:0 0 16px;color:#4f5660;font-size:16px;line-height:1.65;">'
        f"{escape(paragraph)}</p>"
        for paragraph in paragraphs
    )
    detail_html = "".join(
        '<tr><td style="padding:10px 0;border-bottom:1px solid #e8e5de;'
        'color:#757b83;font-size:13px;vertical-align:top;">'
        f'{escape(label)}</td><td style="padding:10px 0 10px 20px;'
        'border-bottom:1px solid #e8e5de;color:#171a1f;font-size:14px;'
        f'font-weight:700;text-align:right;vertical-align:top;">{escape(value)}</td></tr>'
        for label, value in details
    )
    details_block = (
        '<table role="presentation" width="100%" cellspacing="0" cellpadding="0" '
        'style="margin:8px 0 24px;border-collapse:collapse;">'
        f"{detail_html}</table>"
        if details
        else ""
    )
    code_block = (
        '<div style="margin:24px 0;padding:22px 18px;border:1px solid #d9e998;'
        'border-radius:16px;background:#f3fbcf;text-align:center;">'
        '<div style="margin-bottom:8px;color:#687079;font-size:11px;font-weight:800;'
        'letter-spacing:1.4px;text-transform:uppercase;">Your verification code</div>'
        f'<div style="color:#171a1f;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;'
        f'font-size:34px;font-weight:800;letter-spacing:8px;">{escape(code)}</div></div>'
        if code is not None
        else ""
    )
    action_block = (
        '<table role="presentation" cellspacing="0" cellpadding="0" style="margin:8px 0 24px;">'
        '<tr><td style="border-radius:12px;background:#171a1f;">'
        f'<a href="{escape(action_url or "")}" style="display:inline-block;padding:14px 22px;'
        'color:#ffffff;font-size:15px;font-weight:800;text-decoration:none;">'
        f"{escape(action_label or '')}</a></td></tr></table>"
        if action_url is not None
        else ""
    )
    note_block = (
        '<div style="margin-top:8px;padding:14px 16px;border-left:3px solid #c8f135;'
        'background:#f7f6f2;color:#687079;font-size:13px;line-height:1.55;">'
        f"{escape(note)}</div>"
        if note is not None
        else ""
    )
    safe_preheader = escape(preheader)
    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{escape(subject)}</title>
</head>
<body style="margin:0;padding:0;background:#eeece6;font-family:Arial,sans-serif;">
  <div style="display:none;max-height:0;overflow:hidden;opacity:0;">{safe_preheader}</div>
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
         style="background:#eeece6;">
    <tr><td align="center" style="padding:32px 14px;">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0"
             style="max-width:620px;overflow:hidden;border:1px solid #dcd8cf;border-radius:24px;
                    background:#ffffff;box-shadow:0 16px 40px rgba(23,26,31,.08);">
        <tr><td style="padding:24px 32px;background:#171a1f;">
          <table role="presentation" cellspacing="0" cellpadding="0"><tr>
            <td>
              <a href="{escape(home_url)}" style="display:inline-block;text-decoration:none;">
                <img src="cid:{LOGO_CONTENT_ID}" width="54" height="56" alt="BullyMarket"
                     style="display:block;border:0;border-radius:15px;">
              </a>
            </td>
            <td style="padding-left:14px;color:#ffffff;font-size:20px;font-weight:800;">
              BullyMarket
              <div style="margin-top:3px;color:#aeb4bb;font-size:11px;font-weight:400;">
                Friendly stakes. Sharp calls.
              </div>
            </td>
          </tr></table>
        </td></tr>
        <tr><td style="height:6px;background:#c8f135;"></td></tr>
        <tr><td style="padding:36px 32px 32px;">
          <div style="margin-bottom:12px;color:#789b00;font-size:11px;font-weight:800;
                      letter-spacing:1.5px;text-transform:uppercase;">{escape(eyebrow)}</div>
          <h1 style="margin:0 0 18px;color:#171a1f;font-size:30px;line-height:1.15;">
            {escape(title)}
          </h1>
          <p style="margin:0 0 16px;color:#171a1f;font-size:16px;font-weight:700;">
            {escape(greeting)}
          </p>
          {paragraph_html}
          {code_block}
          {details_block}
          {action_block}
          {note_block}
        </td></tr>
        <tr><td style="padding:20px 32px;border-top:1px solid #e8e5de;background:#f7f6f2;
                      color:#7b8188;font-size:12px;line-height:1.6;">
          BullyMarket uses play-money points only. This is an automated message sent by
          <a href="{escape(home_url)}" style="color:#4e6800;font-weight:700;">BullyMarket</a>.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    text_parts = [title, "", greeting, "", *paragraphs]
    if code is not None:
        text_parts.extend(["", f"Verification code: {code}"])
    if details:
        text_parts.extend(["", *(f"{label}: {value}" for label, value in details)])
    if action_url is not None:
        text_parts.extend(["", f"{action_label}: {action_url}"])
    if note is not None:
        text_parts.extend(["", note])
    text_parts.extend(["", "BullyMarket uses play-money points only."])
    return EmailContent(subject=subject, text="\n".join(text_parts), html=html)
