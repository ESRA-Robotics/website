# -*- coding: utf-8 -*-
"""Single source of truth for the legal page content.

Each block is (kind, framer_name, text). kind is "h2", "h3" or "p".
Text may contain newlines; the container CSS uses white-space:pre-wrap,
so they render as line breaks.
"""

ORG = "European Student Robotics Association (ESRA) e.V."
ADDR = "Bayersdorferstraße 8\n80637 München\nGermany"
EMAIL = "info@esrarobotics.eu"

BLOCKS = [
    # ---------------------------------------------------------------- imprint
    ("p", "Imprint Intro",
     "Information pursuant to § 5 of the German Digital Services Act "
     "(Digitale-Dienste-Gesetz, DDG) and § 18 (2) of the German Interstate "
     "Media Treaty (Medienstaatsvertrag, MStV)."),

    ("h2", "Heading Provider", "Provider"),
    ("p", "Provider Details", f"{ORG}\n{ADDR}"),

    ("h2", "Heading Legal Form", "Legal form"),
    ("p", "Legal Form Details",
     "Registered association (eingetragener Verein, e.V.) under German law."),

    ("h2", "Heading Board", "Authorised representatives"),
    ("p", "Board Details",
     "The association is represented by its Executive Board pursuant to § 26 "
     "of the German Civil Code (Bürgerliches Gesetzbuch, BGB):\n"
     "Florian Schroeders, Co-President\n"
     "Doruk Yigiter, Co-President\n"
     "Julian Ritzi, Vice President Finance & Legal"),

    ("h2", "Heading Register", "Register entry"),
    ("p", "Register Details",
     "Register court: Amtsgericht München (Munich Local Court)\n"
     "Register number: VR 211579"),

    ("h2", "Heading VAT", "VAT identification number"),
    ("p", "VAT Details",
     "VAT identification number pursuant to § 27a of the German Value Added "
     "Tax Act (Umsatzsteuergesetz, UStG): DE462819831"),

    ("h2", "Heading Contact", "Contact"),
    ("p", "Contact Details",
     f"Email: {EMAIL}\n"
     "We answer enquiries sent to this address promptly and use it as our "
     "channel for direct communication within the meaning of § 5 (1) no. 2 DDG."),

    ("h2", "Heading Editorial", "Responsible for editorial content"),
    ("p", "Editorial Details",
     "Responsible for the editorial content of this website pursuant to "
     "§ 18 (2) MStV:\n"
     f"Florian Schroeders\n{ORG}\n{ADDR}"),

    ("h2", "Heading Dispute", "Consumer dispute resolution"),
    ("p", "Dispute Details",
     "ESRA e.V. is neither obliged nor willing to participate in dispute "
     "resolution proceedings before a consumer arbitration board within the "
     "meaning of the German Act on Alternative Dispute Resolution in Consumer "
     "Matters (Verbraucherstreitbeilegungsgesetz, VSBG).\n"
     "The European Commission's online dispute resolution platform was "
     "discontinued on 20 July 2025. This page therefore no longer links to it."),

    ("h2", "Heading Liability Content", "Liability for content"),
    ("p", "Liability Content Details",
     "As a service provider, we are responsible for our own content on these "
     "pages in accordance with § 7 (1) DDG and general legislation. Under "
     "§§ 8 to 10 DDG, however, we are not obliged to monitor transmitted or "
     "stored third-party information, or to investigate circumstances that "
     "indicate unlawful activity. Obligations to remove or block the use of "
     "information under general law remain unaffected. Liability in this "
     "respect is possible only from the point at which we become aware of a "
     "specific infringement. If we become aware of any such infringement, we "
     "will remove the content concerned without delay."),

    ("h2", "Heading Liability Links", "Liability for links"),
    ("p", "Liability Links Details",
     "This website contains links to external websites operated by third "
     "parties, over whose content we have no control. We therefore cannot "
     "accept any liability for that external content. The respective provider "
     "or operator of a linked site is always responsible for its content. The "
     "linked pages were checked for possible legal infringements at the time "
     "of linking, and no unlawful content was apparent. Permanent monitoring "
     "of the content of linked pages is not reasonable without concrete "
     "evidence of an infringement. If we become aware of any infringement, we "
     "will remove the link concerned without delay."),

    ("h2", "Heading Copyright", "Copyright"),
    ("p", "Copyright Details",
     "The content and works created by the operators of this site are subject "
     "to German copyright law. Reproduction, adaptation, distribution and any "
     "form of exploitation beyond the limits of copyright require the written "
     "consent of the respective author or creator. Downloads and copies of "
     "this site are permitted for private, non-commercial use only. Where "
     "content on this site was not created by the operator, the copyright of "
     "third parties is respected. Should you become aware of a copyright "
     "infringement nonetheless, please let us know and we will remove the "
     "content concerned without delay.\n"
     "The logos and trade marks of member clubs, universities and partners "
     "shown on this website remain the property of their respective owners.\n"
     "Website design by Royce Malonzo."),

    # ---------------------------------------------------------------- privacy
    ("h2#privacy", "Heading Privacy", "Privacy Policy"),
    ("p", "Privacy Intro",
     "This notice explains what happens to personal data when you visit "
     "esrarobotics.eu. It is provided in accordance with Articles 13 and 14 of "
     "the General Data Protection Regulation (GDPR)."),

    ("h3", "Heading Controller", "1. Controller"),
    ("p", "Controller Details",
     "The controller within the meaning of Article 4 (7) GDPR is:\n"
     f"{ORG}\n{ADDR}\n"
     f"Email: {EMAIL}\n"
     "The association is represented by its Executive Board, named above."),

    ("h3", "Heading DPO", "2. Data protection officer"),
    ("p", "DPO Details",
     "ESRA e.V. is not required to appoint a data protection officer under "
     "Article 37 GDPR or § 38 of the German Federal Data Protection Act "
     "(Bundesdatenschutzgesetz, BDSG), because fewer than twenty people are "
     "permanently engaged in the automated processing of personal data. Please "
     "address data protection enquiries to the contact details above."),

    ("h3", "Heading No Tracking", "3. What this website does not do"),
    ("p", "No Tracking Details",
     "This website sets no cookies and writes nothing to local or session "
     "storage. It contains no analytics, no tracking pixels, no advertising "
     "and no social media plug-ins. No profile is built about you. No consent "
     "banner is required, because nothing is stored on or read from your "
     "device beyond what is strictly necessary to deliver the pages you "
     "request, within the meaning of § 25 of the German Telecommunications "
     "Digital Services Data Protection Act (TDDDG).\n"
     "All fonts, images and scripts are served from this website itself. "
     "Nothing is loaded from a third-party content delivery network, so your "
     "browser does not disclose your IP address to any font or script "
     "provider while you read these pages."),

    ("h3", "Heading Hosting", "4. Hosting and server log files"),
    ("p", "Hosting Details",
     "This website is hosted on GitHub Pages, a service of GitHub, Inc., "
     "88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, USA, a subsidiary "
     "of Microsoft Corporation.\n"
     "When you open a page, your browser necessarily transmits data that "
     "GitHub records in server log files. This typically comprises your IP "
     "address, the date and time of the request, the file requested, the "
     "volume of data transferred, the HTTP status code, the referring page and "
     "information about your browser and operating system.\n"
     "This processing is necessary to deliver the website and to keep it "
     "stable and secure. The legal basis is Article 6 (1) (f) GDPR, our "
     "legitimate interest in providing our website reliably and securely. We "
     "do not merge these logs with other data.\n"
     "Processing takes place in part in the United States. GitHub and "
     "Microsoft are certified under the EU-US Data Privacy Framework, for "
     "which the European Commission adopted an adequacy decision on "
     "10 July 2023, and additionally rely on the European Commission's "
     "standard contractual clauses pursuant to Article 46 GDPR.\n"
     "GitHub's privacy statement: "
     "https://docs.github.com/site-policy/privacy-policies/"
     "github-general-privacy-statement"),

    ("h3", "Heading Email", "5. Contacting us by email"),
    ("p", "Email Details",
     "If you write to us, the data you provide, including your email address "
     "and the content of your message, is processed in order to deal with your "
     "enquiry. The legal basis is Article 6 (1) (b) GDPR where your enquiry "
     "concerns membership or another pre-contractual or contractual matter, "
     "and otherwise Article 6 (1) (f) GDPR, our legitimate interest in "
     "responding to enquiries addressed to us. We keep this correspondence for "
     "as long as it is needed to deal with the matter, and thereafter in "
     "accordance with any statutory retention periods."),

    ("h3", "Heading Applications", "6. Membership applications"),
    ("p", "Applications Details",
     "Applications to join the ESRA network are submitted through an online "
     "form hosted by Tally, operated by Tally BV, Sint-Pietersnieuwstraat 11, "
     "9000 Ghent, Belgium (enterprise number 0776.979.007). The form is not "
     "embedded in this website. It opens on tally.so only when you actively "
     "follow the link, so no data reaches Tally while you browse "
     "esrarobotics.eu.\n"
     "When you submit the form, ESRA e.V. is the controller for the data you "
     "provide and Tally acts as a processor on our behalf under Article 28 "
     "GDPR. The data is stored on servers within the European Union. We "
     "process it to assess and administer your application; the legal basis is "
     "Article 6 (1) (b) GDPR.\n"
     "Tally's privacy policy: https://tally.so/help/privacy-policy"),

    ("h3", "Heading External Links", "7. Links to other websites"),
    ("p", "External Links Details",
     "This website links to the websites of member clubs, universities, "
     "partners and other third parties. Once you follow such a link this "
     "notice no longer applies, and the data protection practices of the site "
     "you have moved to take over. We have no control over those websites and "
     "accept no responsibility for how they handle your data."),

    ("h3", "Heading Rights", "8. Your rights"),
    ("p", "Rights Details",
     "Under the GDPR you have the right to request access to the personal data "
     "we hold about you (Article 15), to have inaccurate data corrected "
     "(Article 16), to have your data erased (Article 17), to have processing "
     "restricted (Article 18), to receive your data in a portable format "
     "(Article 20) and to object to processing based on legitimate interests "
     "(Article 21). Where processing rests on consent, you may withdraw that "
     "consent at any time with effect for the future.\n"
     "To exercise any of these rights, write to the contact details above."),

    ("h3", "Heading Complaint", "9. Right to lodge a complaint"),
    ("p", "Complaint Details",
     "If you consider that the processing of your personal data infringes the "
     "GDPR, you may lodge a complaint with a supervisory authority, in "
     "particular in the Member State of your habitual residence, your place of "
     "work or the place of the alleged infringement. The authority responsible "
     "for ESRA e.V. is:\n"
     "Bayerisches Landesamt für Datenschutzaufsicht (BayLDA)\n"
     "Promenade 18, 91522 Ansbach, Germany\n"
     "Telephone: +49 981 180093-0\n"
     "Email: poststelle@lda.bayern.de"),

    ("h3", "Heading Automated", "10. Automated decision-making"),
    ("p", "Automated Details",
     "We do not use automated decision-making, including profiling, within the "
     "meaning of Article 22 GDPR."),

    ("h3", "Heading Provision", "11. Providing your data"),
    ("p", "Provision Details",
     "You are under no statutory or contractual obligation to provide personal "
     "data to us. Reading this website requires no personal data beyond the "
     "connection data described above. If you choose not to provide the "
     "information requested in the membership application form, however, we "
     "may be unable to process your application."),

    ("h3", "Heading Changes", "12. Changes to this notice"),
    ("p", "Changes Details",
     "We may update this notice to reflect changes to the website or to legal "
     "requirements. The version published here is always the one that applies.\n"
     "Last updated: 16 September 2026."),
]
