using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;
using System.Web.Script.Serialization;
using Microsoft.Win32;

[assembly:System.Reflection.AssemblyCompany("Amir Rahimi")]
[assembly:System.Reflection.AssemblyProduct("Cable Label Studio Update")]
class UpdateWorker {
    static string Q(string value){return "\""+value.Replace("\"","\\\"")+"\"";}
    [STAThread] static int Main(string[] a){
        if(a.Length!=5)return 2;
        var serializer=new JavaScriptSerializer();int result=1;
        try{
            Thread.Sleep(1000);
            string args="/silent /mode update /dir "+Q(a[1])+" /log "+Q(a[4])+" /data-dir "+Q(a[2]);
            using(var key=Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Uninstall\CableLabelStudio")){
                string installed=key==null?null:key.GetValue("InstallLocation") as string;
                if(!String.Equals(installed,a[1],StringComparison.OrdinalIgnoreCase))args+=" /no-registry /no-shortcuts";
            }
            using(var process=Process.Start(new ProcessStartInfo(a[0],args){UseShellExecute=false,CreateNoWindow=true})){
                process.WaitForExit();result=process.ExitCode;
            }
            var state=serializer.Deserialize<Dictionary<string,object>>(File.ReadAllText(a[3],Encoding.UTF8));
            state["state"]=result==0?"complete":"error";
            state["error"]=result==0?null:"UPDATE_INSTALL_FAILED: "+result;
            // Server is stopped by the installer before files are replaced.
            SaveState(a[3],serializer.Serialize(state));
        }catch(Exception ex){
            try{File.AppendAllText(a[4],ex+Environment.NewLine,Encoding.UTF8);
                var state=serializer.Deserialize<Dictionary<string,object>>(File.ReadAllText(a[3],Encoding.UTF8));
                state["state"]="error";state["error"]=ex.Message;SaveState(a[3],serializer.Serialize(state));}catch{}
        }finally{
            try{Process.Start(new ProcessStartInfo(Path.Combine(a[1],"CableLabelStudio.exe"),"--no-browser --data-dir "+Q(a[2])){UseShellExecute=false,CreateNoWindow=true});}catch{}
        }
        return result;
    }
    static void SaveState(string path,string text){
        string temporary=path+".worker.tmp";File.WriteAllText(temporary,text,new UTF8Encoding(false));
        if(File.Exists(path))File.Replace(temporary,path,null);else File.Move(temporary,path);
    }
}
