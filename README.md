# ESRA Robotics Website

Statischer Export der ESRA-Website (ursprünglich in Framer gebaut, gehostet unter
`studentrobotics.eu`) für den Umzug auf `esrarobotics.eu` via GitHub Pages.

## Struktur

- `index.html` — Startseite (alle Sektionen: Mission, What We Do, Network, Partners, Application, Contact)
- `imprint.html` — Impressum (`/imprint`)
- `assets/` — Bilder, Icons, Fonts-Ladelogik und das Framer-Laufzeit-JS (Animationen/Interaktionen)
- `CNAME` — Custom-Domain-Datei für GitHub Pages (`esrarobotics.eu`)

## Bekannte offene Punkte

- Die Impressum-Seite listet noch `info@studentrobotics.eu` als Kontakt-E-Mail — ggf. auf die neue Domain umstellen.
- Änderungen an Texten/Bildern sind direkt in `index.html` / `imprint.html` möglich (einfache Fund-und-Ersetz-Änderungen).
  Größere Layout-Umbauten sind aufwändiger, da der Code aus Framer generiert ist (gehashte CSS-Klassennamen, mehrere Responsive-Breakpoints).
- Das Laufzeit-JS in `assets/` (react/motion/framer-Module) stammt von Framers öffentlichem CDN und wurde lokal gespiegelt,
  damit die Seite ohne Framer-Backend funktioniert.
