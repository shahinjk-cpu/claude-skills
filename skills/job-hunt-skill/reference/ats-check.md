# ATS check (after every tailored CV PDF)

`python3 SKILL_DIR/scripts/ats_check.py --cv <pdf> --posting <posting.txt|URL> --title "<posted title>" --workspace <ws>`

Act on every section of the report:
- **Parsing:** fix every ❌ and ⚠ (selectable text, contact details near the top, standard headings, dates, glued lines, fonts, file name).
- **Missing but true** (in `profile.md`): add where it fits naturally.
- **Related evidence:** describe what the user actually did, in the posting's words only when accurate (Kalman filter → state estimation is fine).
- **Not in profile / Do NOT claim:** keep out of the CV; prepare an honest interview answer instead.
- **Title:** echo the posting's title in the headline only when it's truthful.
- **Screening topics** (location, work authorisation, salary, years of experience…): go over them with the user before they apply. Most automatic rejections happen there.
- The CV stays plain and honest: visible text only, real skills only.
