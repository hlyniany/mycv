import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CopyIcon, CheckIcon, XIcon } from 'lucide-react';
type Language = 'en' | 'ua';
const PROMPTS = {
  en: `You are an expert technical recruiter assistant and resume analyst.

I will provide you with:

1. A JSON Resume (fetched from URL below)

2. A job description (I will paste it after this prompt)

**Resume JSON URL:** https://YOUR_GITHUB_USERNAME.github.io/YOUR_REPO/resume.json

**Your task:**

1. Fetch and parse the JSON Resume from the URL above

2. Read the job description I paste below

3. Analyze the match between the candidate's profile and the role

4. Output a structured report:

---

## Match Analysis

### ✅ Strong matches

[Skills, experience, keywords that directly align]

### ⚠️ Partial matches

[Areas where candidate has adjacent but not exact experience]

### ❌ Gaps

[Requirements not covered by the resume]

### 🏆 Overall fit score

[X/10 with one-sentence rationale]

### 💬 Suggested talking points for screening call

[3–5 specific questions based on gaps or ambiguities]

---

**Job description:**

[PASTE JOB DESCRIPTION HERE]`,
  ua: `Ти — експерт з технічного рекрутингу та аналізу резюме.

Я надам тобі:

1. JSON Resume (за URL нижче)

2. Опис вакансії (вставлю після цього промту)

**URL резюме у форматі JSON:** https://YOUR_GITHUB_USERNAME.github.io/YOUR_REPO/resume.json

**Твоє завдання:**

1. Завантажити та розпарсити JSON Resume за вказаним URL

2. Прочитати опис вакансії, який я вставлю нижче

3. Проаналізувати відповідність профілю кандидата та вимог ролі

4. Сформувати структурований звіт:

---

## Аналіз відповідності

### ✅ Сильні збіги

[Навички, досвід, ключові слова, які прямо відповідають вимогам]

### ⚠️ Часткові збіги

[Сфери, де кандидат має суміжний, але не точний досвід]

### ❌ Прогалини

[Вимоги, які не покриті резюме]

### 🏆 Загальна оцінка відповідності

[X/10 з одним реченням обґрунтування]

### 💬 Рекомендовані питання для скринінгового дзвінка

[3–5 конкретних питань на основі прогалин або неоднозначностей]

---

**Опис вакансії:**

[ВСТАВТЕ ОПИС ВАКАНСІЇ ТУТ]`
};
export function RecruiterPromptBar() {
  const [isExpanded, setIsExpanded] = useState(false);
  const [language, setLanguage] = useState<Language>('en');
  const [copied, setCopied] = useState(false);
  const closeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(PROMPTS[language]);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };
  const handleMouseEnter = () => {
    if (closeTimeoutRef.current) {
      clearTimeout(closeTimeoutRef.current);
      closeTimeoutRef.current = null;
    }
    setIsExpanded(true);
  };
  const handleMouseLeave = () => {
    closeTimeoutRef.current = setTimeout(() => {
      setIsExpanded(false);
    }, 150);
  };
  return (
    <div
      className="sticky top-0 z-50"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}>
      
      {/* Collapsed Bar — light, airy, single centered line */}
      <div className="bg-white/90 backdrop-blur-sm border-b border-gray-200">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full h-11 flex items-center justify-center group transition-colors hover:bg-gray-50/80"
          aria-expanded={isExpanded}
          aria-label={isExpanded ? 'Collapse AI panel' : 'Expand AI panel'}>
          
          <span className="flex items-center gap-1.5 text-[13px] tracking-wide text-gray-600 group-hover:text-gray-900 transition-colors">
            <motion.span
              animate={{
                x: isExpanded ? 2 : 0,
                rotate: isExpanded ? 90 : 0
              }}
              transition={{
                duration: 0.15
              }}
              className="text-gray-400 group-hover:text-violet-500">
              
              ▸
            </motion.span>
            <span className="font-medium">Analyze with AI</span>
          </span>
        </button>
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {isExpanded &&
        <motion.div
          initial={{
            height: 0,
            opacity: 0
          }}
          animate={{
            height: 'auto',
            opacity: 1
          }}
          exit={{
            height: 0,
            opacity: 0
          }}
          transition={{
            duration: 0.18,
            ease: [0.22, 1, 0.36, 1]
          }}
          className="overflow-hidden bg-white border-b border-gray-200 shadow-sm">
          
            <div className="max-w-4xl mx-auto px-6 py-5 flex flex-col gap-4 min-h-[280px] max-h-[40vh]">
              {/* Controls */}
              <div className="flex items-center justify-between gap-3 flex-wrap">
                <div className="flex items-center gap-3">
                  <p className="text-sm text-gray-600 hidden sm:block">
                    Copy this prompt into ChatGPT or Claude with a job
                    description.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  {/* Language toggle */}
                  <div className="flex gap-0.5 bg-gray-100 rounded-md p-0.5">
                    <button
                    onClick={() => setLanguage('en')}
                    className={`px-3 py-1 rounded text-xs font-medium transition-all ${language === 'en' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    aria-pressed={language === 'en'}>
                    
                      EN
                    </button>
                    <button
                    onClick={() => setLanguage('ua')}
                    className={`px-3 py-1 rounded text-xs font-medium transition-all ${language === 'ua' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
                    aria-pressed={language === 'ua'}>
                    
                      UA
                    </button>
                  </div>

                  <motion.button
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 hover:bg-gray-800 text-white rounded-md text-xs font-medium transition-colors"
                  whileTap={{
                    scale: 0.96
                  }}
                  aria-label="Copy prompt">
                  
                    {copied ?
                  <>
                        <CheckIcon className="w-3.5 h-3.5" />
                        <span>Copied!</span>
                      </> :

                  <>
                        <CopyIcon className="w-3.5 h-3.5" />
                        <span>Copy prompt</span>
                      </>
                  }
                  </motion.button>

                  <button
                  onClick={() => setIsExpanded(false)}
                  className="p-1.5 hover:bg-gray-100 rounded-md transition-colors"
                  aria-label="Close panel">
                  
                    <XIcon className="w-4 h-4 text-gray-500" />
                  </button>
                </div>
              </div>

              {/* Prompt code block */}
              <AnimatePresence mode="wait">
                <motion.div
                key={language}
                initial={{
                  opacity: 0,
                  y: 6
                }}
                animate={{
                  opacity: 1,
                  y: 0
                }}
                exit={{
                  opacity: 0,
                  y: -6
                }}
                transition={{
                  duration: 0.12
                }}
                className="flex-1 overflow-auto bg-gray-50 rounded-md p-4 border border-gray-200">
                
                  <pre className="text-gray-700 text-xs md:text-[13px] font-mono leading-relaxed whitespace-pre-wrap">
                    {PROMPTS[language]}
                  </pre>
                </motion.div>
              </AnimatePresence>
            </div>
          </motion.div>
        }
      </AnimatePresence>
    </div>);

}