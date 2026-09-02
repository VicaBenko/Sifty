# רצף הפעלה — Superpowers · Sift

**תאריך:** 28.08.2026 · **קדם:** `08-handover-to-development.md`

תיקיית העבודה: `%USERPROFILE%\Sift`.

---

## 1. מה Superpowers עושה ולמה נבחר

תוסף ל-Claude Code שהוא בעיקר מתודולוגיה אכופה: סיעור מוחות ← תוכנית ← מימוש ע"י תת-סוכנים ← TDD ← ביקורת קוד ← סגירה.

שתי מכניקות נושאות את כל התועלת:

**תת-סוכן טרי לכל משימה.** התוכנית מפורקת למשימות של 2-5 דקות עם נתיבי קבצים מדויקים וצעד אימות. כל משימה מקבלת סוכן נקי שקורא רק את הספק, התוכנית והמשימה שלו. ההקשר לא מתנוון לאורך בנייה של שבועות.

**הספק הוא סמכות מחייבת.** ביקורת הקוד בסוף כל משימה נמדדת מול הספק והתוכנית, וחוסמת בעיות קריטיות. *"The spec is the binding authority, the plan is its argument."*

**למה דווקא כאן:** 44 דרישות שנופלות בשקט בלי מנגנון כיסוי; רכיב FR-E שבו באג מוחק תמונות מכל המכשירים; ושלוש דרישות חוסמות שצריכות להפוך לקריטריון ביקורת אוטומטי. המחיר — איטי ויקר יותר בטוקנים — משתלם בפרויקט שמוחק קבצים בלי חזרה.

---

## 2. התקנה, פעם אחת

`/plugin` **אינו קיים באפליקציית Claude Code הדסקטופ** (באג ידוע, issue #42142). ההתקנה חייבת לרוץ מהטרמינל.

```
winget install Anthropic.ClaudeCode
```

לסגור ולפתוח מחדש את החלון, ואז:

```
claude --version
claude plugin marketplace add obra/superpowers-marketplace
claude plugin install superpowers@superpowers-marketplace
cd /d "%USERPROFILE%\Sift"
git init
claude
```

**מבחן שהתוסף חי:** לבקש בשיחה משהו כמו "בוא נבנה רשימת משימות". אם הוא פותח בשאלות במקום בקוד — עובד.

**git נדרש.** Superpowers עובד בענפים ומבצע commit בסוף כל משימה. בלעדיו אין דרך לחזור אחורה כשמשימה נשברת.

---

## 3. פיצול הספק

הכישור `writing-plans` מבצע בדיקת כיסוי עצמית ומזהיר: *"If the spec covers multiple independent subsystems, it should have been broken into sub-project specs."*

| קובץ | דרישות | מצב |
|---|---|---|
| `specs/00-global-constraints.md` | — | חל על **כל** תוכנית ומשימה |
| `specs/01-indexing.md` | FR-A1–A10, FR-B1–B6 | מוכן לתכנון |
| `specs/02-query.md` | FR-C1–C9 | תלוי בקטלוג בלבד |
| `specs/03-server-ui.md` | FR-H1–H8, FR-D1–D6 | נפתח אחרי מסמך 09 |
| `specs/04-quarantine-delete.md` | FR-E1–E13 | הרכיב הרגיש. לבדוק בכבדות |
| `specs/05-settings-cost-log.md` | FR-F1–F5, FR-G1–G3 | חוצה-מערכת, אחרון |

**סדר בנייה:** מקור ואינדוקס ← שאילתה ← ממשק ← ביצוע ← הגדרות ויומן.

הביצוע אחרי הממשק בכוונה: כך אפשר לראות תוצאות ולוודא שהן נכונות לפני שנכתב קוד שנוגע בקבצים של המשתמש.

---

## 4. הלולאה לכל ספק

**א. תוכנית.** לבקש תוכנית מול הספק, בלי קוד, ולדרוש בסוף אמירה מפורשת איזו דרישה בספק אינה מכוסה באף משימה:

```
The spec is specs/01-indexing.md. It is the binding authority.
specs/00-global-constraints.md applies to every task in this plan.

Write an implementation plan against it. Do not write code yet.

When the plan is done, tell me explicitly which requirement in the
spec is not covered by any task in the plan.
```

**ב. אישור אנושי.** הנקודה היחידה של שליטה בכל המחזור. אחריה הסוכן רץ לבד. אין לדלג.

**ג. מימוש.** פירוק לתת-משימות, סוכן נקי לכל אחת, מבחן נכשל לפני קוד שמתקן אותו, ביקורת מול הספק בסוף כל משימה.

---

## 5. שלוש דרישות שביקורת חייבת לחסום עליהן

| דרישה | מה קורה בלעדיה | נבדק ב |
|---|---|---|
| **FR-H2** — localhost בלבד | כל מי שברשת רואה את כל הגלריה | AC-9 |
| **FR-E10** — לעולם לא להעביר קבצים | תמונות נמחקות מכל המכשירים בלי אישור | AC-3, AC-4 |
| **FR-F4** — תקרת הוצאה חודשית | האינדוקס האוטומטי מוציא כסף בלי לשאול | AC-6 |

מפורטות ב-`specs/00-global-constraints.md`, שחל על כל תוכנית.

---

## 6. מקורות

- [obra/superpowers](https://github.com/obra/superpowers/)
- [Installing on Claude Code](https://deepwiki.com/obra/superpowers/2.1-installing-on-claude-code)
- [Claude Code — Advanced setup](https://code.claude.com/docs/en/setup)
- [Claude Code Desktop אין בו /plugin — issue #42142](https://github.com/anthropics/claude-code/issues/42142)
