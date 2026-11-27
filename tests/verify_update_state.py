"""Exercise the actual C# update state writer with Windows sharing locks."""
import json
import os
from pathlib import Path
import subprocess
import uuid

root=Path(__file__).resolve().parents[1]
case=root/'.installer-qa'/('state-race-'+uuid.uuid4().hex[:8]);case.mkdir(parents=True)
probe=case/'Probe.cs'
probe.write_text(r'''
using System;
using System.IO;
using System.Reflection;
using System.Threading;
class StateRaceProbe {
 static void Save(string path,string text){
  typeof(UpdateWorker).GetMethod("SaveState",BindingFlags.Static|BindingFlags.NonPublic).Invoke(null,new object[]{path,text});
 }
 static int Main(string[] args){
  string path=Path.Combine(args[0],"state.json");File.WriteAllText(path,"old-complete-state");
  Exception failure=null;Thread thread;
  using(var reader=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)){
   thread=new Thread(()=>{try{Save(path,"new-complete-state");}catch(Exception e){failure=e;}});thread.Start();
   Thread.Sleep(450);
   using(var read=new StreamReader(new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.ReadWrite))){if(read.ReadToEnd()!="old-complete-state")throw new Exception("State changed while replacement was locked");}
  }
  thread.Join(8000);if(thread.IsAlive||failure!=null)throw new Exception("Atomic replacement did not recover",failure);
  if(File.ReadAllText(path)!="new-complete-state")throw new Exception("Incomplete state");
  if(Directory.GetFiles(args[0],"*.tmp").Length!=0)throw new Exception("Temporary state leaked");
  Console.WriteLine("PASS transient sharing lock retains old bytes and recovers atomically");
  File.Delete(path);Directory.CreateDirectory(path);bool rejected=false;
  try{Save(path,"invalid");}catch(TargetInvocationException){rejected=true;}
  if(!rejected||!Directory.Exists(path)||Directory.GetFiles(args[0],"*.tmp").Length!=0)throw new Exception("Persistent failure was hidden or leaked temporary state");
  Console.WriteLine("PASS persistent destination error is reported without deleting the destination");return 0;
 }
}
''',encoding='utf-8')
compiler=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
exe=case/'Probe.exe'
subprocess.run([str(compiler),'/nologo','/main:StateRaceProbe','/reference:System.Web.Extensions.dll','/out:'+str(exe),str(root/'installer/UpdateWorker.cs'),str(probe)],check=True)
subprocess.run([str(exe),str(case)],check=True,timeout=20)
report={'passed':True,'checks':['real Windows sharing lock recovers with atomic old/new states','persistent destination failure remains explicit and cleans temporary state']}
(root/'verification/update-state.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
