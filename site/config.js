// Deployment settings. The defaults suit the local server (api/server.py serving this folder).
// On GitHub Pages the API lives elsewhere (deploy/README.md): set api to its base URL and scans to "un".
window.TRAVAUX = {
  api: "",                         // base URL of the API without a trailing slash; "" is the same origin
  scans: "local",                  // "local": scans served by the API at /pdf/; "un": links to the UN's own copy (undocs.org)
  label: "working edition v0.9",   // shown in the header
  title: "",                       // the page title, if it should differ from the one in index.html
  version: "v0.9",                 // the version, as the footer and the "how to cite" line give it
  // Who answers for the site. The footer and the About page show what is filled in here, and nothing is invented:
  // a public deployment needs the three of them (deploy/README.md).
  author: "",                      // the name to cite and to credit
  affiliation: "",                 // the institution
  contact: "",                     // an email address or a web address for corrections and feedback
  url: "",                         // the address of the site, for the citation
};
