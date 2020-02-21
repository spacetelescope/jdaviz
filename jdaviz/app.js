
checkNotebookContext() {
    this.notebook_context = document.getElementById("ipython-main-app");
    return this.notebook_context;
};

loadRemoteCSS() {
    window.addEventListener('resize', function () { console.log("RESIZING"); });
    var muiIconsSheet = document.createElement('link');
    muiIconsSheet.type = 'text/css';
    muiIconsSheet.rel = 'stylesheet';
    muiIconsSheet.href = 'https://cdn.jsdelivr.net/npm/@mdi/font@4.x/css/materialdesignicons.min.css';
    document.getElementsByTagName('head')[0].appendChild(muiIconsSheet);
    return true;
};