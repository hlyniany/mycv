import React from 'react';
import {
  MailIcon,
  PhoneIcon,
  MapPinIcon,
  GithubIcon,
  LinkedinIcon } from
'lucide-react';
export function ResumePreview() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12 bg-white">
      {/* Header */}
      <header className="border-b border-gray-200 pb-8 mb-8">
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 mb-3">
          Vitaliy Hlynianyi-Zhuk
        </h1>
        <p className="text-xl text-gray-600 mb-4">Senior Software Engineer</p>

        <div className="flex flex-wrap gap-4 text-sm text-gray-600">
          <div className="flex items-center gap-2">
            <MailIcon className="w-4 h-4" />
            <span>vitaliy@example.com</span>
          </div>
          <div className="flex items-center gap-2">
            <PhoneIcon className="w-4 h-4" />
            <span>+380 XX XXX XXXX</span>
          </div>
          <div className="flex items-center gap-2">
            <MapPinIcon className="w-4 h-4" />
            <span>Kyiv, Ukraine</span>
          </div>
          <div className="flex items-center gap-2">
            <GithubIcon className="w-4 h-4" />
            <a
              href="https://github.com/hlyniany"
              className="hover:text-gray-900 transition-colors">
              
              github.com/hlyniany
            </a>
          </div>
          <div className="flex items-center gap-2">
            <LinkedinIcon className="w-4 h-4" />
            <a href="#" className="hover:text-gray-900 transition-colors">
              LinkedIn
            </a>
          </div>
        </div>
      </header>

      {/* Summary */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Professional Summary
        </h2>
        <p className="text-gray-700 leading-relaxed">
          Experienced software engineer with 5+ years of expertise in full-stack
          development, specializing in React, TypeScript, and Node.js. Proven
          track record of delivering scalable web applications and leading
          technical initiatives. Passionate about clean code, user experience,
          and continuous learning.
        </p>
      </section>

      {/* Experience */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Work Experience
        </h2>

        <div className="mb-6">
          <div className="flex justify-between items-start mb-2">
            <div>
              <h3 className="text-xl font-semibold text-gray-900">
                Senior Software Engineer
              </h3>
              <p className="text-gray-600">Tech Company Inc.</p>
            </div>
            <span className="text-sm text-gray-500">2021 - Present</span>
          </div>
          <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
            <li>
              Led development of customer-facing web applications using React
              and TypeScript
            </li>
            <li>
              Architected and implemented RESTful APIs serving 100K+ daily
              active users
            </li>
            <li>Mentored junior developers and conducted code reviews</li>
            <li>
              Improved application performance by 40% through optimization
              techniques
            </li>
          </ul>
        </div>

        <div className="mb-6">
          <div className="flex justify-between items-start mb-2">
            <div>
              <h3 className="text-xl font-semibold text-gray-900">
                Software Engineer
              </h3>
              <p className="text-gray-600">Startup Solutions</p>
            </div>
            <span className="text-sm text-gray-500">2019 - 2021</span>
          </div>
          <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
            <li>
              Developed and maintained multiple client projects using modern web
              technologies
            </li>
            <li>
              Collaborated with designers to implement pixel-perfect UI
              components
            </li>
            <li>Integrated third-party APIs and payment systems</li>
          </ul>
        </div>
      </section>

      {/* Skills */}
      <section className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-4">
          Technical Skills
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Frontend</h4>
            <p className="text-sm text-gray-700">
              React, TypeScript, Next.js, Tailwind CSS
            </p>
          </div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Backend</h4>
            <p className="text-sm text-gray-700">
              Node.js, Express, PostgreSQL, MongoDB
            </p>
          </div>
          <div>
            <h4 className="font-semibold text-gray-900 mb-2">Tools</h4>
            <p className="text-sm text-gray-700">Git, Docker, AWS, CI/CD</p>
          </div>
        </div>
      </section>

      {/* Education */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-4">Education</h2>
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-xl font-semibold text-gray-900">
              Bachelor of Computer Science
            </h3>
            <p className="text-gray-600">
              National Technical University of Ukraine
            </p>
          </div>
          <span className="text-sm text-gray-500">2015 - 2019</span>
        </div>
      </section>
    </div>);

}