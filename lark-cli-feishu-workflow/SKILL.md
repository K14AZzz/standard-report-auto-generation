---
name: lark-cli-feishu-workflow
description: "Use lark-cli for authenticated Feishu/Lark spreadsheet work: configure or bind the CLI, authorize a user, inspect values/formulas/styles, make minimal typed writes or style-only edits, and read back results for verification. Trigger for Feishu spreadsheet data entry, formatting, row/column operations, formula checks, or batch edits where reliable API-backed changes are preferred."
---

# Lark CLI Feishu Workflow

Use the complete `lark-cli` binary as the primary path for Feishu spreadsheet operations. Keep browser/Computer Use and direct Python Open API calls as fallback only when the CLI genuinely cannot perform the requested operation.

## 1. Authentication and identity

Before any CLI operation, run:

```bash
lark-cli whoami
lark-cli auth status --json --verify
```

Use `--as user` for the user's spreadsheets and personal resources. Use `--as bot` only for app-owned resources. Never print app secrets or access tokens.

If the CLI is not configured:

```bash
lark-cli config init --new
```

If an Agent credential source already exists, prefer `lark-cli config bind` after confirming the intended identity policy. Do not silently create a parallel app when binding is appropriate.

For user authorization, request the narrowest needed domain, normally Sheets:

```bash
lark-cli auth login --domain sheets --no-wait --json
```

Follow split-flow: show the returned `verification_url`, generate a PNG QR with `lark-cli auth qrcode <url> --output ./auth.png`, wait for the user to confirm, then personally finish with `lark-cli auth login --device-code <device_code>`. Never reuse expired device codes or alter the URL.

## 2. Locate and inspect the workbook

For a new task, first resolve sheet IDs and dimensions:

```bash
lark-cli sheets +workbook-info --url "<spreadsheet-url>"
lark-cli sheets +sheet-info --url "<spreadsheet-url>" --sheet-name "<sheet>" --include merges,row_heights,col_widths,hidden_rows,hidden_cols,frozen
```

Read before writing. For values only use `+csv-get`; for formulas/styles use:

```bash
lark-cli sheets +cells-get --url "<spreadsheet-url>" \
  --sheet-name "<sheet>" --range "A1:Z100" \
  --include value,formula,style
```

For large ranges use `--output-path` and check `complete`, `truncated`, `has_more`, and actual ranges. Identify title, header, data, subtotal/total, and blank rows from content—not row-number patterns alone. Respect merged cells and hidden rows/columns.

## 2a. Troubleshoot `client secret is invalid`

If `lark-cli auth login` returns `device authorization failed: The client secret is invalid`, stop before requesting Sheets authorization. This is an application-credential failure, not a user OAuth or spreadsheet-permission failure.

Check that the App ID and App Secret come from the same Feishu/Lark custom app, that the secret was not regenerated after it was copied, and that the value is not a user token, tenant token, placeholder, or text with extra quotes/whitespace. Prefer stdin so the secret is not placed in shell history:

```bash
printf '%s\n' "$FEISHU_APP_SECRET" | \
  lark-cli config init \
    --app-id "$FEISHU_APP_ID" \
    --app-secret-stdin \
    --brand feishu
```

Use `--brand lark` for Lark tenants. If the existing profile is stale, rerun `lark-cli config init` with the corrected pair (or `config init --new` for a new profile). Never print or commit credentials.

Verify the corrected configuration without exposing secrets:

```bash
lark-cli whoami
lark-cli auth status --json --verify
```

Only then start a fresh device flow; never reuse an expired device code or cached verification URL:

```bash
lark-cli auth login --domain sheets --no-wait --json
lark-cli auth login --device-code '<fresh-device-code>'
```

If the error persists, create/select a valid custom app and enable the required Sheets scopes. Each recipient should use their own app credentials unless a shared app is intentionally managed through secure secret storage.

## 3. Minimal, typed writes

- Preserve numeric/date/formula types; do not stringify numbers merely to force display.
- Prefer formulas for derived totals and ratios when the source range is known; verify the formula landed.
- For one or more precise regions use `+cells-set`; use `--writes` for scattered regions in one request.
- For typed tabular data use `+table-put` with explicit `dtypes` and `formats`.
- For new rows/columns, use `+dim-insert --inherit-style before|after`, then restore row height if needed.
- Never overwrite non-empty cells in a fill/repair task unless the user explicitly authorizes it; use `--allow-overwrite=false` when protection is required.

## 4. Style-only edits and format alignment

Before changing styles, snapshot the target and reference with `+cells-get --include style` and preserve the user's manual template/data regions. Compare by relative cell role and content type (title, header, data, total; currency, count, ratio), not only by row position.

Use style-only commands so values/formulas remain untouched:

```bash
lark-cli sheets +cells-set-style --spreadsheet-token "<token>" --sheet-id "<sheet-id>" \
  --range "H29:H321" --number-format "0.0%"
```

For many non-contiguous ranges, prefer `+styles-put` or `+cells-batch-set-style` after confirming their schemas. Do not use `+cells-set --copy-to-range` as a format brush: it can copy values/formulas too.

Typical number formats:

- ROAS / rates: `0.0%` or the exact format from the reference template
- Currency integer: `¥#,##0` (or the exact template format)
- Currency one decimal: `¥#,##0.0`
- Counts: `#,##0`

If a format command succeeds, still read back `value,formula,style`; an accepted request is not proof of correct display. Check representative first/middle/last rows and totals. Confirm formulas remain formulas and the template region is unchanged.

## 5. Verification checklist

After every write or style operation:

1. Re-read the exact modified ranges with `+cells-get`.
2. Check displayed values, `number_format`, borders/colors when relevant, and formulas.
3. Confirm no unintended neighboring cells, merged ranges, or manual template areas changed.
4. For totals, independently compare the total row with the contributing data rows.
5. Record any unsupported format or permission issue instead of claiming completion.

For destructive commands (`+cells-clear`, `+dim-delete`, `+batch-update`, etc.), run `--dry-run`, show the scope, obtain explicit user confirmation, then append `--yes` and execute.

## 6. Fallback order

1. Complete `lark-cli` shortcut with user identity.
2. `lark-cli api` raw endpoint only if no shortcut exists.
3. Existing OAuth + Python `urllib` Open API helper when CLI cannot authenticate or expose the needed endpoint.
4. Computer Use/browser only for UI-only behavior such as a display control unavailable through API.

Keep all intermediate reads and verification artifacts local to the current working directory or another approved non-user-data location. Do not expose credentials in logs or responses.
