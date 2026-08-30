# העברה לפיתוח — Sift

**תאריך:** 28.08.2026 · **מצב:** תכנון סגור, פיתוח טרם התחיל
**נמען:** מי שממשיך לשלב המימוש

---

## 1. מה המוצר

כלי מקומי הרץ על כל מערכת הפעלה, עם ממשק בדפדפן, שמאנדקס תיקיית תמונות ומאפשר למחוק תמונות **לפי תיאור מילולי באנגלית** — למשל `photos with a monitor showing code`.

**הרעיון הטכני המרכזי:** לא מחפשים בתמונות. עוברים עליהן פעם אחת, מייצרים לכל תמונה רשימת אובייקטים מובנית + תיאור, ומחפשים בטקסט הזה. שאילתה = חיתוך קבוצות מדויק, לא דמיון וקטורי.

**הבטחת הבטיחות:** האפליקציה **מעתיקה** תמונות לתיקיית הסגר ולעולם לא מעבירה. המחיקה מתבצעת רק אחרי שהמשתמש סקר את התיקייה ואישר במפורש.

**היקף:** פרויקט אישי. אין לקוחות, אין מודל תשלום, אין דרישות הפצה.

---

## 2. סדר קריאה

| # | קובץ | למה |
|---|---|---|
| 1 | `07-process-summary.md` | **התחל כאן.** כל הסיפור מההתחלה, כולל מה השתנה ולמה |
| 2 | `01-product-brief.md` | מה המוצר ולמי |
| 3 | `02-decision-memo-001-architecture.md` | **החשוב ביותר.** ארבע הכרעות ארכיטקטוניות עם הראיות |
| 4 | `03-decision-memo-002-platform.md` | הפלטפורמה — מנוע מקומי + ממשק בדפדפן |
| 5 | `06-prd.md` | **מסמך המקור לפיתוח.** 44 דרישות ממוספרות |
| 6 | `05-validation-gate-result.md` | מה תוקף אמפירית ומה נשאר פתוח |
| 7 | `04-validation-gate-protocol.md` | שיטת הבדיקה. רב-פעמית |

**אם יש זמן לשניים בלבד:** `06-prd.md` + `02-decision-memo-001-architecture.md`.

---

## 3. שתי הכרעות שאסור לבטל בלי לקרוא את הנימוק

### א. העתקה, לעולם לא העברה

תיקיית iCloud היא ספק סנכרון. **מחיקת קובץ ממנה מתפשטת לכל המכשירים** (מתועד רשמית אצל Apple). **התנהגות ההעברה אינה מתועדת כלל**, ויש עדות שהעברה לכונן אחר מתפרשת כמחיקה.

שתי הפעולות המותרות מול תיקיית המקור: **העתקה החוצה**, ו**מחיקה במקום לאחר אישור**. אין שלישית.

מי שיחליף את ההעתקה בהעברה "כי זה יעיל יותר" ימחק למשתמש תמונות מהטלפון לפני שאישר. ראה מסמך 02, החלטה 1.

### ב. תיוג מובנה, לא חיפוש דמיון

הגישה המתבקשת היא embeddings מסוג CLIP/SigLIP. **היא לא תעבוד כאן.** מודלים כאלה אינם קושרים בין אובייקטים: כשהשאילתה מזכירה אובייקט קטן או לא-ראשון, הדיוק צונח מ-99.6% ל-52-72%, **ולא משתפר עם מודלים גדולים יותר.**

הארכיטקטורה קיימת בדיוק כדי לעקוף זאת. ראה מסמך 02, החלטה 2, עם המקורות.

---

## 4. מה תוקף אמפירית

**500 תמונות אמיתיות. עלות $0.54.**

| ממצא | סטטוס |
|---|---|
| תשתית מקצה לקצה — 500/500, אפס שגיאות | ✅ |
| איכות תיוג — 7 אובייקטים לתמונה בחציון, כולל קטנים | ✅ |
| שאילתה חד-משמעית — 99% כיסוי, 84% דיוק | ✅ עבר |
| עלות — כ-$0.001 לתמונה | ✅ נמדד |
| דיוק בשאילתות מרובות-אובייקטים | ⚠️ **לא נמדד** |

**הסיכון הפתוח והמענה:** ה"אמת" הידנית לא הייתה מהימנה לשאילתות המורכבות. הבחירה המודעת: לשאת את הסיכון, כי הארכיטקטורה הופכת דיוק לא מושלם לעבודה מיותרת ולא לאובדן תמונות. **FR-G2 סוגר אותו** — המוצר מתעד בכל סבב כמה פריטים הוצאו מתיקיית ההסגר. מדד דיוק שנאסף מעצמו.

`validation/` מכילה את ערכת המבחן. רב-פעמית — אפשר להריץ שוב על מדגם אחר, מודל אחר, או אחרי שינוי בפרומפט.

---

## 5. עבודה עם Superpowers

Superpowers מצפה ל**ספק (Spec)** — מסמך דרישות שהתוכנית מתייחסת אליו כסמכות מחייבת. מהתיעוד: *"The spec is the binding authority, the plan is its argument."* ביקורת הקוד בכל משימה נמדדת מולו.

**`06-prd.md` הוא הקובץ שנועד לתפקיד הזה** — והוא כבר פוצל.
הספקים המוכנים נמצאים תחת `specs/`, ורצף ההפעלה המלא ב-`docs/10-superpowers-runbook.md`.

### פיצול הספק

הכישור `writing-plans` מבצע בדיקת כיסוי עצמית ומזהיר: *"If the spec covers multiple independent subsystems, it should have been broken into sub-project specs."* ה-PRD מכסה שמונה קבוצות. **הצעת פיצול:**

| קובץ הספק | דרישות | הערה |
|---|---|---|
| `specs/00-global-constraints.md` | — | חל על **כל** תוכנית ומשימה |
| `specs/01-indexing.md` | FR-A1–A10, FR-B1–B6 | הבסיס |
| `specs/02-query.md` | FR-C1–C9 | תלוי בקטלוג בלבד |
| `specs/03-server-ui.md` | FR-H1–H8, FR-D1–D6 | **חסום** עד שנכתב `docs/09-ux-decisions.md` |
| `specs/04-quarantine-delete.md` | FR-E1–E13 | **הרכיב הרגיש.** לבדוק בכבדות |
| `specs/05-settings-cost-log.md` | FR-F1–F5, FR-G1–G3 | חוצה-מערכת, אפשר אחרון |

**סדר בנייה מומלץ:** מקור ואינדוקס ← שאילתה ← ממשק ← ביצוע ← הגדרות ויומן.

הביצוע אחרי הממשק **בכוונה** — כך אפשר לראות תוצאות ולוודא שהן נכונות לפני שנכתב קוד שנוגע בקבצים של המשתמש.

### Global Constraints

הבלוק המלא נמצא ב-`specs/00-global-constraints.md` וחל על כל תוכנית. מובא כאן לעיון:

```
- Target platforms: Windows, macOS, Linux from one codebase. No OS-specific
  logic outside the filesystem layer.
- The engine runs locally. The UI is served by a local HTTP server that
  listens on localhost ONLY. Never bind 0.0.0.0 or any external interface.
- Access to the local server is gated by a token generated at startup.
- Only two operations are permitted against the user's source folder:
  read, and delete-in-place after explicit user approval in that same session.
  NEVER move files out of the source folder. NEVER write into it.
- Quarantine is populated by COPY. Originals stay in place until approval.
- The quarantine folder must be OUTSIDE the source folder; refuse otherwise.
- Only 384px downscaled derivatives are sent to the external tagging provider.
  Original files never leave the machine.
- Catalog, operation log and API key are stored locally only.
- The tagging provider sits behind a swappable interface.
- Query language is English. No Hebrew query parsing in scope.
- Query response under 1s on a 50k-photo catalog, excluding verification.
- Engine, query engine and UI are separable; the engine must run and be
  testable headless.
- External failures (network, provider, disk) must never leave the catalog or
  the quarantine folder in an inconsistent state.
```

### שלוש דרישות חוסמות

| דרישה | למה | נבדק ב |
|---|---|---|
| **FR-H2** — localhost בלבד | שרת חשוף פותח את כל הגלריה לכל מי שברשת | AC-9 |
| **FR-E10** — לעולם לא להעביר | הפרה = מחיקת תמונות בלי אישור | AC-3 |
| **FR-F4** — תקרת הוצאה | האינדוקס אוטומטי; בלי תקרה הוא מוציא כסף בלי בקשה | AC-6 |

---

## 6. מה פתוח ומחכה להכרעה

| נושא | מצב |
|---|---|
| **שלב UX** | **לא בוצע. הפער הידוע היחיד.** מסך התוצאות הוא לב המוצר וטרם עוצב |
| שפת הממשק | לא הוכרעה. שפת השאילתה אנגלית; ממשק בעברית עם חיפוש באנגלית הוא חיכוך לפתור בעיצוב |
| מסך פתיחה ומבנה ניווט | לא הוכרעו |
| היקף זיכרון השחרורים | ההנחה: שחרור תקף לשאילתה שבה נעשה. לא אושר סופית |
| ארכיטקטורה, אפיקים וסיפורים | לא בוצעו |
| בחירת סטאק | פתוחה במכוון. ה-PRD לא מכתיב שפה או פריימוורק |

---

## 7. מבנה החבילה

```
docs/
  01-product-brief.md                    מה המוצר ולמי
  02-decision-memo-001-architecture.md   ארבע הכרעות ארכיטקטוניות
  03-decision-memo-002-platform.md       פלטפורמה ופריסה
  04-validation-gate-protocol.md         שיטת הבדיקה
  05-validation-gate-result.md           תוצאות הבדיקה
  06-prd.md                              דרישות — מסמך המקור לפיתוח
  07-process-summary.md                  סיכום התהליך המלא
  08-handover-to-development.md          המסמך הזה

validation/                              ערכת המבחן, חמישה שלבים
  step1_sample.py                        דגימה (קריאה בלבד, מעתיק בלבד)
  step2_tag.py                           תיוג מובנה, ניתן לעצירה והמשך
  step3_label.py                         מייצר דף תיוג ידני
  step4_score.py                         כיסוי ודיוק מול קריטריון
  step5_report.py                        דוח HTML עם התמונות
  queries.json                           שאילתות ונרדפות
  sift_common.py                         עזרים, כולל זיהוי placeholders
```

**הערה על `validation/`:** קוד לצורך מדידה, לא בסיס למוצר. אפשר ללמוד ממנו את הפרומפט ואת מבנה הקטלוג — הוא מדגים את שרשרת התיוג מקצה לקצה — אבל הוא לא נכתב כדי להישאר.

**המסמכים בעברית.** ניתן להפיק גרסה אנגלית אם נדרש.
