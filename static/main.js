document.addEventListener('DOMContentLoaded', function(){
    const main = document.querySelector('main');
    if(main){ main.style.opacity = 0; setTimeout(()=> main.style.transition = 'opacity 600ms',10); setTimeout(()=> main.style.opacity = 1,20); }
});
