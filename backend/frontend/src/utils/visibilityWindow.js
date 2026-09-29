// Framework-free continuous visibility gate; fake clocks can verify all transitions.
export function visibilityWindow({emit,visible,delay=1000,setTimer=setTimeout,clearTimer=clearTimeout}) {
  let ratio=0,timer=null,stopped=false;
  const cancel=()=>{if(timer!==null)clearTimer(timer);timer=null;};
  function update(next=ratio) {
    ratio=next;cancel();
    if(stopped || ratio<.5 || !visible())return;
    timer=setTimer(()=>{timer=null;if(!stopped && ratio>=.5 && visible())void emit();},delay);
  }
  return {update,stop(){stopped=true;cancel();}};
}
