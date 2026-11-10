export function groupDigits(value){
 const [integer,...fraction]=String(value??'').split('.');
 return integer.replace(/\B(?=(\d{3})+(?!\d))/g,',')+(fraction.length?'.'+fraction.join('.'):'');
}
