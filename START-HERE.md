# מאיפה מתחילים — Sift

התיקייה הזאת היא תיקיית העבודה של הפרויקט. הכל קורה כאן.

---

## מה יש בתיקייה

```
docs/          שמונת מסמכי התכנון. 06-prd.md הוא מסמך המקור
specs/         חמישה ספקים — מה לבנות, בסדר הזה
validation/    ערכת המדידה מהשלב הקודם. ללמוד ממנה, לא לבנות עליה
START-HERE.md  הקובץ הזה
```

---

## שלב 0 — התקנה, פעם אחת

`/plugin` **לא עובד באפליקציית Claude Code הדסקטופ.** זה באג ידוע. חייבים טרמינל.

פתחי PowerShell:

```powershell
irm https://claude.ai/install.ps1 | iex
```

סגרי ופתחי מחדש את החלון, ואז:

```powershell
claude --version
claude plugin marketplace add obra/superpowers-marketplace
claude plugin install superpowers@superpowers-marketplace
```

ואז:

```powershell
cd "$HOME\Sift"
git init
claude
```

**מבחן שהתוסף חי:** כתבי בשיחה "בוא נבנה רשימת משימות".
אם הוא שואל שאלות במקום לכתוב קוד — עובד. אם הוא ישר כותב קוד — לא הותקן.

---

## שלב 1 — לסגור את ה-UX

זה הפער היחיד שנשאר פתוח בתכנון, וספק 3 חסום בגללו.

הדביקי בשיחה:

```
Read docs/06-prd.md and docs/08-handover-to-development.md.

Planning is closed except for one stage: UX. The results screen was
never designed, and specs/03-server-ui.md is blocked on it.

I want to brainstorm that screen. Do not write code.

The screen shows results of an English free-text query over a photo
gallery, with a confidence level and a match reason per photo, and lets
me release photos before they go to the quarantine folder.

The open questions are listed at the bottom of specs/03-server-ui.md.

Ask me one question at a time. When we are done, write the decisions
to docs/09-ux-decisions.md.
```

הוא ייכנס לכישור ה-brainstorming. זה לוקח זמן, וזה בכוונה.

---

## שלב 2 — הלולאה, חמש פעמים

סדר הבנייה, ואסור לשנות אותו:

| # | ספק | למה בסדר הזה |
|---|---|---|
| 1 | `specs/01-indexing.md` | הבסיס. הכל תלוי בקטלוג |
| 2 | `specs/02-query.md` | תלוי בקטלוג בלבד |
| 3 | `specs/03-server-ui.md` | חסום עד שיש `docs/09-ux-decisions.md` |
| 4 | `specs/04-quarantine-delete.md` | **הרכיב שנוגע בקבצים שלך.** רק אחרי שראית תוצאות נכונות בעיניים |
| 5 | `specs/05-settings-cost-log.md` | חוצה-מערכת |

לכל ספק, שלושה צעדים:

**א. לבקש תוכנית** — הדביקי, עם מספר הספק הנכון:

```
The spec is specs/01-indexing.md. It is the binding authority.
specs/00-global-constraints.md applies to every task in this plan.

Write an implementation plan against it. Do not write code yet.

When the plan is done, tell me explicitly which requirement in the
spec is not covered by any task in the plan.
```

**ב. את קוראת את התוכנית ומאשרת.**
זו הנקודה שבה את שולטת בפרויקט. אחריה הוא רץ לבד. אל תדלגי עליה.

**ג. לתת לו לממש.** הוא מפרק לתת-משימות קצרות, כל אחת מקבלת סוכן נקי, כותב מבחן שנכשל לפני קוד שמתקן אותו, ובסוף כל משימה עושה ביקורת מול הספק.

---

## שלוש דרישות שביקורת חייבת לחסום עליהן

| דרישה | מה קורה בלעדיה |
|---|---|
| **FR-H2** — localhost בלבד | כל מי שברשת רואה את כל הגלריה |
| **FR-E10** — לעולם לא להעביר קבצים | תמונות נמחקות מכל המכשירים בלי אישור |
| **FR-F4** — תקרת הוצאה חודשית | האינדוקס האוטומטי מוציא כסף בלי לשאול |

הן מפורטות ב-`specs/00-global-constraints.md`, והוא חל על כל תוכנית.
