using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows.Forms;
using Microsoft.Win32;

[assembly: AssemblyTitle("Cable Label Studio Setup")]
[assembly: AssemblyProduct("Cable Label Studio")]
[assembly: AssemblyVersion("1.0.0.0")]

public class PackageManifest {
    public string product {get;set;}
    public string version {get;set;}
    public Dictionary<string,string> files {get;set;}
}

[ComImport, Guid("00021401-0000-0000-C000-000000000046")]
public class ShellLinkObject {}
[ComImport, InterfaceType(ComInterfaceType.InterfaceIsIUnknown), Guid("000214F9-0000-0000-C000-000000000046")]
public interface IShellLinkW {
    void GetPath([Out,MarshalAs(UnmanagedType.LPWStr)] StringBuilder file,int count,IntPtr findData,uint flags);
    void GetIDList(out IntPtr id);
    void SetIDList(IntPtr id);
    void GetDescription([Out,MarshalAs(UnmanagedType.LPWStr)] StringBuilder value,int count);
    void SetDescription([MarshalAs(UnmanagedType.LPWStr)] string value);
    void GetWorkingDirectory([Out,MarshalAs(UnmanagedType.LPWStr)] StringBuilder value,int count);
    void SetWorkingDirectory([MarshalAs(UnmanagedType.LPWStr)] string value);
    void GetArguments([Out,MarshalAs(UnmanagedType.LPWStr)] StringBuilder value,int count);
    void SetArguments([MarshalAs(UnmanagedType.LPWStr)] string value);
    void GetHotkey(out short value);
    void SetHotkey(short value);
    void GetShowCmd(out int value);
    void SetShowCmd(int value);
    void GetIconLocation([Out,MarshalAs(UnmanagedType.LPWStr)] StringBuilder value,int count,out int index);
    void SetIconLocation([MarshalAs(UnmanagedType.LPWStr)] string value,int index);
    void SetRelativePath([MarshalAs(UnmanagedType.LPWStr)] string value,uint reserved);
    void Resolve(IntPtr window,uint flags);
    void SetPath([MarshalAs(UnmanagedType.LPWStr)] string value);
}

public static class Program {
    public static string Product = "CableLabelStudio";
    public static string Exe = "CableLabelStudio.exe";
    public static string RegPath = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\CableLabelStudio";
    public static Dictionary<string,string> Args = new Dictionary<string,string>(StringComparer.OrdinalIgnoreCase);
    public static string InstalledPath() { using(var key=Registry.CurrentUser.OpenSubKey(RegPath)){return key==null?null:key.GetValue("InstallLocation") as string;} }
    [STAThread] public static int Main(string[] args) {
        for(int i=0;i<args.Length;i++){
            if(args[i].StartsWith("/")){
                string k=args[i].Substring(1); string v="true";
                if(i+1<args.Length && !args[i+1].StartsWith("/"))v=args[++i];
                Args[k]=v;
            }
        }
        Application.EnableVisualStyles(); Application.SetCompatibleTextRenderingDefault(false);
        try {
            string mode=Get("mode","install"), dir=Get("dir",InstalledPath()??Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"Programs",Product));
            // Run maintenance from a temporary copy, allowing removal of the installed maintenance binary.
            if(!Args.ContainsKey("relocated") && mode=="uninstall" && String.Equals(Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location),Path.GetFullPath(dir),StringComparison.OrdinalIgnoreCase)){
                string copy=Path.Combine(Path.GetTempPath(),"CableLabelStudio-Maintenance-"+Guid.NewGuid().ToString("N")+".exe");
                File.Copy(Assembly.GetExecutingAssembly().Location,copy);
                string line=String.Join(" ",args.Select(Quote).ToArray())+" /relocated";
                Process.Start(new ProcessStartInfo(copy,line)); return 0;
            }
            if(Args.ContainsKey("silent")){
                var engine=new Engine(dir,mode,!Args.ContainsKey("no-registry"),!Args.ContainsKey("no-shortcuts"),null,null);
                engine.Run(); return 0;
            }
            Application.Run(new Wizard(dir,mode)); return 0;
        } catch(Exception e) {
            try{File.AppendAllText(Get("log",Path.Combine(Path.GetTempPath(),"CableLabelStudio-setup-error.log")),e.ToString()+Environment.NewLine);}catch{}
            if(!Args.ContainsKey("silent"))MessageBox.Show(e.Message,"Cable Label Studio",MessageBoxButtons.OK,MessageBoxIcon.Error);
            return 1;
        }
    }
    public static string Get(string key,string fallback){return Args.ContainsKey(key)?Args[key]:fallback;}
    public static string Quote(string s){return "\""+s.Replace("\"","\\\"")+"\"";}
}

public class Engine {
    string target,mode,logPath; bool registry,shortcuts; Action<string> log; Action<int> progress;
    public Engine(string target,string mode,bool registry,bool shortcuts,Action<string> log,Action<int> progress){
        this.target=Path.GetFullPath(target).TrimEnd(Path.DirectorySeparatorChar);this.mode=mode;this.registry=registry;this.shortcuts=shortcuts;this.log=log;this.progress=progress;
        string logDir=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),Program.Product,"logs");Directory.CreateDirectory(logDir);
        logPath=Program.Get("log",Path.Combine(logDir,"setup-"+DateTime.Now.ToString("yyyyMMdd-HHmmss")+".log"));
    }
    void Log(string text){string line=DateTime.Now.ToString("HH:mm:ss")+"  "+text;File.AppendAllText(logPath,line+Environment.NewLine,Encoding.UTF8);if(log!=null)log(line);}
    void Progress(int n){if(progress!=null)progress(n);}
    string Safe(string root,string relative){
        string path=Path.GetFullPath(Path.Combine(root,relative));
        if(!path.StartsWith(Path.GetFullPath(root).TrimEnd('\\')+"\\",StringComparison.OrdinalIgnoreCase))throw new InvalidDataException("Unsafe package path");
        return path;
    }
    PackageManifest Manifest(string root){
        string file=Path.Combine(root,"package-manifest.json");
        if(!File.Exists(file))return null;
        var m=new JavaScriptSerializer(){MaxJsonLength=10000000}.Deserialize<PackageManifest>(File.ReadAllText(file,Encoding.UTF8));
        if(m==null||m.product!=Program.Product||m.files==null)throw new InvalidDataException("Invalid installation manifest");return m;
    }
    static string Hash(string path){using(var sha=SHA256.Create())using(var f=File.OpenRead(path))return BitConverter.ToString(sha.ComputeHash(f)).Replace("-","").ToLowerInvariant();}
    void DeleteOwnedFile(string file){if(File.Exists(file)){File.SetAttributes(file,File.GetAttributes(file)&~FileAttributes.ReadOnly);File.Delete(file);}}
    void CopyOwnedFile(string source,string file){Directory.CreateDirectory(Path.GetDirectoryName(file));if(File.Exists(file))File.SetAttributes(file,File.GetAttributes(file)&~FileAttributes.ReadOnly);File.Copy(source,file,true);}
    void StopApp(){
        string app=Path.Combine(target,Program.Exe);
        if(!File.Exists(app))return;
        Log("Stopping installed application...");
        using(var process=Process.Start(new ProcessStartInfo(app,"--stop"){UseShellExecute=false,CreateNoWindow=true,WindowStyle=ProcessWindowStyle.Hidden}))process.WaitForExit(10000);
        for(int i=0;i<50;i++){
            bool running=false;
            foreach(var p in Process.GetProcessesByName("CableLabelStudio")){
                try{if(String.Equals(p.MainModule.FileName,app,StringComparison.OrdinalIgnoreCase))running=true;}catch{}finally{p.Dispose();}
            }
            if(!running)return;Thread.Sleep(100);
        }
        throw new IOException("Application is still running. Close active print jobs and try again.");
    }
    public void Run(){
        if(!new[]{"install","repair","update","uninstall"}.Contains(mode))throw new ArgumentException("Invalid setup mode");
        string root=Path.GetPathRoot(target).TrimEnd('\\');
        string windows=Environment.GetFolderPath(Environment.SpecialFolder.Windows).TrimEnd('\\');
        if(target.Length<root.Length+3||target.StartsWith(windows+"\\",StringComparison.OrdinalIgnoreCase)||String.Equals(target,windows,StringComparison.OrdinalIgnoreCase))throw new IOException("Choose a dedicated application folder.");
        PackageManifest old=Manifest(target);
        if(Directory.Exists(target) && Directory.EnumerateFileSystemEntries(target).Any() && old==null)throw new IOException("The destination contains unrelated files. Choose an empty folder.");
        if(mode=="uninstall"||mode=="repair")if(old==null)throw new IOException("No installation was found in this folder.");
        Log("Cable Label Studio 1.0.0 · "+mode);Log("Destination: "+target);Log("Data is preserved in LocalAppData\\CableLabelStudio.");Progress(2);
        StopApp();
        if(mode=="uninstall"){
            int index=0;
            foreach(var name in old.files.Keys){string file=Safe(target,name);DeleteOwnedFile(file);Progress(10+(++index*75/Math.Max(1,old.files.Count)));}
            string manifest=Path.Combine(target,"package-manifest.json");File.Delete(manifest);
            string maintenance=Path.Combine(target,"CableLabelStudio-Setup.exe");if(File.Exists(maintenance))File.Delete(maintenance);
            foreach(var dir in Directory.GetDirectories(target,"*",SearchOption.AllDirectories).OrderByDescending(d=>d.Length))if(!Directory.EnumerateFileSystemEntries(dir).Any())Directory.Delete(dir);
            if(!Directory.EnumerateFileSystemEntries(target).Any())Directory.Delete(target);
            if(registry){using(var run=Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run",true)){if(run!=null)run.DeleteValue("CableLabelStudio",false);}Registry.CurrentUser.DeleteSubKeyTree(Program.RegPath,false);}
            if(shortcuts)RemoveShortcuts();Log("Uninstalled. User data and backups were preserved.");Progress(100);return;
        }
        string stage=target+".stage-"+Guid.NewGuid().ToString("N"),backup=target+".rollback-"+Guid.NewGuid().ToString("N");
        var registryBefore=registry?SnapshotRegistry():null;
        var linksBefore=shortcuts?LinkPaths().ToDictionary(p=>p,p=>File.Exists(p)?File.ReadAllBytes(p):null):null;
        bool startFolderBefore=Directory.Exists(StartFolder());
        Directory.CreateDirectory(stage);Directory.CreateDirectory(backup);
        bool overlay=false;
        try{
            Log("Extracting offline application package...");
            using(var payload=Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip")){
                if(payload==null)throw new InvalidDataException("Missing embedded payload");
                using(var zip=new ZipArchive(payload,ZipArchiveMode.Read)){
                    int i=0;
                    foreach(var entry in zip.Entries){
                        if(String.IsNullOrEmpty(entry.Name))continue;
                        string file=Safe(stage,entry.FullName);Directory.CreateDirectory(Path.GetDirectoryName(file));
                        using(var input=entry.Open())using(var output=File.Create(file))input.CopyTo(output);
                        Progress(5+(++i*45/zip.Entries.Count));
                    }
                }
            }
            var manifest=Manifest(stage);if(manifest==null)throw new InvalidDataException("Missing package manifest");
            Log("Verifying SHA-256 checksums...");
            foreach(var entry in manifest.files)if(Hash(Safe(stage,entry.Key))!=entry.Value)throw new InvalidDataException("Checksum failed: "+entry.Key);
            Progress(60);
            Directory.CreateDirectory(target);
            // Copy only product-owned files; preserve all external data.
            if(old!=null)foreach(var name in old.files.Keys.Concat(new[]{"package-manifest.json","CableLabelStudio-Setup.exe"})){
                string existing=Safe(target,name);if(!File.Exists(existing))continue;
                string copy=Safe(backup,name);Directory.CreateDirectory(Path.GetDirectoryName(copy));File.Copy(existing,copy,true);
            }
            overlay=true;Log("Installing verified files...");
            int installed=0;
            foreach(var entry in manifest.files.Keys.Concat(new[]{"package-manifest.json"})){
                string to=Safe(target,entry);CopyOwnedFile(Safe(stage,entry),to);
                if(++installed%50==0)Log("Installed "+installed+" files");Progress(60+(installed*30/(manifest.files.Count+1)));
            }
            string self=Assembly.GetExecutingAssembly().Location,maintenance=Path.Combine(target,"CableLabelStudio-Setup.exe");
            if(!String.Equals(self,maintenance,StringComparison.OrdinalIgnoreCase))File.Copy(self,maintenance,true);
            if(old!=null)foreach(var obsolete in old.files.Keys.Except(manifest.files.Keys))DeleteOwnedFile(Safe(target,obsolete));
            if(shortcuts)CreateShortcuts();if(registry)Register();
            Log("Installation complete. Browser interface and print engine are ready.");Log("Setup log: "+logPath);Progress(100);
        }catch{
            try{
                if(registry)RestoreRegistry(registryBefore);
                if(shortcuts){
                    foreach(var link in linksBefore){
                        if(link.Value==null){if(File.Exists(link.Key))File.Delete(link.Key);}
                        else{Directory.CreateDirectory(Path.GetDirectoryName(link.Key));File.WriteAllBytes(link.Key,link.Value);}
                    }
                    if(!startFolderBefore&&Directory.Exists(StartFolder())&&!Directory.EnumerateFileSystemEntries(StartFolder()).Any())Directory.Delete(StartFolder());
                }
            }catch(Exception rollback){Log("Integration rollback error: "+rollback.Message);}
            if(overlay){
                Log("Installation failed. Restoring previous application files...");
                var failed=Manifest(stage);
                if(failed!=null)foreach(var file in failed.files.Keys.Concat(new[]{"package-manifest.json","CableLabelStudio-Setup.exe"})){
                    string path=Safe(target,file);
                    if(!File.Exists(Safe(backup,file))&&!String.Equals(path,Assembly.GetExecutingAssembly().Location,StringComparison.OrdinalIgnoreCase)){
                        try{DeleteOwnedFile(path);}catch(Exception restore){Log("Rollback could not remove "+file+": "+restore.Message);}
                    }
                }
                foreach(var file in Directory.GetFiles(backup,"*",SearchOption.AllDirectories)){
                    string relative=file.Substring(backup.Length+1),to=Safe(target,relative);
                    if(String.Equals(to,Assembly.GetExecutingAssembly().Location,StringComparison.OrdinalIgnoreCase))continue;
                    try{CopyOwnedFile(file,to);}catch(Exception restore){Log("Rollback could not restore "+relative+": "+restore.Message);}
                }
            }
            throw;
        }finally{DeleteOwnedStage(stage);DeleteOwnedStage(backup);}
    }
    void DeleteOwnedStage(string path){
        // Stage directories are fresh siblings created by this installer; never delete a computed user target.
        string full=Path.GetFullPath(path);
        if((full.StartsWith(target+".stage-",StringComparison.OrdinalIgnoreCase)||full.StartsWith(target+".rollback-",StringComparison.OrdinalIgnoreCase))&&Directory.Exists(full)){
            foreach(var file in Directory.GetFiles(full,"*",SearchOption.AllDirectories))File.SetAttributes(file,File.GetAttributes(file)&~FileAttributes.ReadOnly);
            Directory.Delete(full,true);
        }
    }
    void Register(){using(var key=Registry.CurrentUser.CreateSubKey(Program.RegPath)){
        key.SetValue("DisplayName","Cable Label Studio");key.SetValue("DisplayVersion","1.0.0");key.SetValue("Publisher","Cable Label Studio");key.SetValue("InstallLocation",target);
        key.SetValue("DisplayIcon",Path.Combine(target,Program.Exe));
        string setup=Program.Quote(Path.Combine(target,"CableLabelStudio-Setup.exe"));
        key.SetValue("UninstallString",setup+" /mode uninstall /dir "+Program.Quote(target));
        key.SetValue("ModifyPath",setup+" /mode repair /dir "+Program.Quote(target));key.SetValue("NoRepair",0,RegistryValueKind.DWord);
    }Log("Registered per-user Windows installation.");}
    Dictionary<string,Tuple<object,RegistryValueKind>> SnapshotRegistry(){
        using(var key=Registry.CurrentUser.OpenSubKey(Program.RegPath)){
            if(key==null)return null;
            return key.GetValueNames().ToDictionary(name=>name,name=>Tuple.Create(key.GetValue(name,null,RegistryValueOptions.DoNotExpandEnvironmentNames),key.GetValueKind(name)));
        }
    }
    void RestoreRegistry(Dictionary<string,Tuple<object,RegistryValueKind>> before){
        if(before==null){Registry.CurrentUser.DeleteSubKeyTree(Program.RegPath,false);return;}
        using(var key=Registry.CurrentUser.CreateSubKey(Program.RegPath)){
            foreach(var name in key.GetValueNames())key.DeleteValue(name,false);
            foreach(var entry in before)key.SetValue(entry.Key,entry.Value.Item1,entry.Value.Item2);
        }
    }
    void CreateLink(string path,string file,string args){
        Directory.CreateDirectory(Path.GetDirectoryName(path));
        object instance=new ShellLinkObject();
        try{
            IShellLinkW link=(IShellLinkW)instance;
            link.SetPath(file);link.SetArguments(args);link.SetWorkingDirectory(target);
            link.SetDescription("Cable Label Studio");link.SetIconLocation(Path.Combine(target,Program.Exe),0);link.SetShowCmd(1);
            ((System.Runtime.InteropServices.ComTypes.IPersistFile)instance).Save(path,true);
        }finally{Marshal.FinalReleaseComObject(instance);}
    }
    string StartFolder(){return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs),"Cable Label Studio");}
    string[] LinkPaths(){return new[]{Path.Combine(StartFolder(),"Cable Label Studio.lnk"),Path.Combine(StartFolder(),"Maintenance.lnk"),Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),"Cable Label Studio.lnk")};}
    void CreateShortcuts(){
        Directory.CreateDirectory(StartFolder());
        CreateLink(Path.Combine(StartFolder(),"Cable Label Studio.lnk"),Path.Combine(target,Program.Exe),"");
        CreateLink(Path.Combine(StartFolder(),"Maintenance.lnk"),Path.Combine(target,"CableLabelStudio-Setup.exe"),"/mode repair /dir "+Program.Quote(target));
        CreateLink(Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),"Cable Label Studio.lnk"),Path.Combine(target,Program.Exe),"");
        Log("Created Start menu and desktop shortcuts.");
    }
    void RemoveShortcuts(){
        string desktop=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),"Cable Label Studio.lnk");if(File.Exists(desktop))File.Delete(desktop);
        string folder=StartFolder();foreach(var name in new[]{"Cable Label Studio.lnk","Maintenance.lnk"}){string p=Path.Combine(folder,name);if(File.Exists(p))File.Delete(p);}if(Directory.Exists(folder)&&!Directory.EnumerateFileSystemEntries(folder).Any())Directory.Delete(folder);
    }
}

public class Wizard:Form {
    Color dark=Color.FromArgb(16,45,53),teal=Color.FromArgb(18,121,111),ink=Color.FromArgb(30,61,61);
    Panel side,body;Label title,subtitle,steps;ComboBox language,mode;TextBox path;Button browse,next,back;CheckBox launch;RichTextBox log;ProgressBar progress;int stage=0;string initialMode;
    string[][] words=new[]{
        new[]{"Welcome to your label workspace","به فضای کار چاپ لیبل خوش آمدید","مرحباً بك في مساحة طباعة الملصقات"},
        new[]{"A precise, offline workspace for Brother PT-E550W.","فضای کاری دقیق و آفلاین برای Brother PT-E550W.","مساحة عمل دقيقة دون اتصال لطابعة Brother PT-E550W."},
        new[]{"Choose an operation","عملیات را انتخاب کنید","اختر العملية"},
        new[]{"New installation","نصب جدید","تثبيت جديد"},new[]{"Repair installation","تعمیر نصب","إصلاح التثبيت"},new[]{"Update application","ارتقای برنامه","تحديث التطبيق"},new[]{"Uninstall application","حذف نصب برنامه","إزالة التطبيق"},
        new[]{"Installation folder","مسیر نصب","مجلد التثبيت"},new[]{"Browse…","انتخاب…","استعراض…"},new[]{"Continue","ادامه","متابعة"},new[]{"Back","بازگشت","رجوع"},new[]{"Install / apply","نصب / اجرا","تثبيت / تطبيق"},new[]{"Installation progress","پیشرفت عملیات نصب","تقدم عملية التثبيت"},
        new[]{"All done","عملیات انجام شد","اكتملت العملية"},new[]{"Close","بستن","إغلاق"},new[]{"Launch Cable Label Studio","اجرای استودیو لیبل کابل","تشغيل استوديو الملصقات"},
        new[]{"Your templates, uploads and history are preserved during repair, update and uninstall.","قالب‌ها، آپلودها و سابقه هنگام تعمیر، ارتقا و حذف نصب حفظ می‌شوند.","تُحفظ القوالب والملفات والسجل أثناء الإصلاح والتحديث والإزالة."},
        new[]{"Ready to apply","آمادهٔ اجرا","جاهز للتطبيق"},new[]{"Files are verified with SHA-256. No Python installation is required.","فایل‌ها با SHA-256 بررسی می‌شوند. به نصب Python نیازی نیست.","تُتحقق الملفات باستخدام SHA-256. لا يلزم تثبيت Python."},
        new[]{"Setup failed. See the log below.","عملیات ناموفق بود. لاگ پایین را بررسی کنید.","فشلت العملية. راجع السجل أدناه."},new[]{"Cancel setup?","از نصب خارج می‌شوید؟","هل تريد إلغاء التثبيت؟"},
        new[]{"1  Welcome\n\n2  Installation\n\n3  Ready to print","۱  خوش‌آمدگویی\n\n۲  نصب و تنظیم\n\n۳  آمادهٔ چاپ","١  ترحيب\n\n٢  التثبيت\n\n٣  جاهز للطباعة"},
        new[]{"The interface opens in your browser. USB printing needs the Brother driver; Access files need the 64-bit Microsoft Access engine.","محیط برنامه در مرورگر باز می‌شود. چاپ USB به درایور Brother و فایل Access به موتور ۶۴ بیت Microsoft Access نیاز دارد.","تفتح الواجهة في المتصفح. تحتاج طباعة USB إلى برنامج Brother وملفات Access إلى محرك Microsoft Access بنسخة ٦٤ بت."}
    };
    int Lang{get{return language==null||language.SelectedIndex<0?1:language.SelectedIndex;}}
    string T(int index){return words[index][Lang];}
    Label LabelAt(string text,int x,int y,int w,int height,int size,bool bold){var n=new Label(){Text=text,Location=new Point(x,y),Size=new Size(w,height),ForeColor=ink,Font=new Font("Segoe UI",size,bold?FontStyle.Bold:FontStyle.Regular)};body.Controls.Add(n);return n;}
    Button ButtonAt(string text,int x,int y,int w){var b=new Button(){Text=text,Location=new Point(x,y),Size=new Size(w,40),FlatStyle=FlatStyle.Flat,BackColor=Color.White,ForeColor=ink,Cursor=Cursors.Hand};b.FlatAppearance.BorderColor=Color.FromArgb(210,224,215);body.Controls.Add(b);return b;}
    public Wizard(string destination,string action){
        initialMode=action;Text="Cable Label Studio · Setup";ClientSize=new Size(960,620);MinimumSize=MaximumSize=Size;StartPosition=FormStartPosition.CenterScreen;BackColor=Color.FromArgb(249,251,249);Font=new Font("Segoe UI",10);MaximizeBox=false;
        try{Icon=Icon.ExtractAssociatedIcon(Assembly.GetExecutingAssembly().Location);}catch{}
        side=new Panel(){Dock=DockStyle.Left,Width=235,BackColor=dark};Controls.Add(side);
        var brand=new Label(){Text="CABLE LABEL\nSTUDIO",Location=new Point(28,38),Size=new Size(200,90),ForeColor=Color.White,Font=new Font("Segoe UI",22,FontStyle.Bold)};side.Controls.Add(brand);
        var caption=new Label(){Text="WINDOWS / OFFLINE\nBROTHER PT-E550W",Location=new Point(30,135),Size=new Size(190,60),ForeColor=Color.FromArgb(137,180,170),Font=new Font("Segoe UI",9)};side.Controls.Add(caption);
        steps=new Label(){Location=new Point(28,270),Size=new Size(190,170),ForeColor=Color.FromArgb(218,233,221),Font=new Font("Segoe UI",11)};side.Controls.Add(steps);
        side.Controls.Add(new Label(){Text="VERSION 1.0.0\nLOCAL, BY DESIGN",Location=new Point(30,550),Size=new Size(180,60),ForeColor=Color.FromArgb(126,159,154),Font=new Font("Segoe UI",8)});
        body=new Panel(){Dock=DockStyle.Fill,Padding=new Padding(20)};Controls.Add(body);body.BringToFront();
        language=new ComboBox(){DropDownStyle=ComboBoxStyle.DropDownList,Location=new Point(495,20),Size=new Size(180,30)};language.Items.AddRange(new object[]{"English","فارسی","العربية"});body.Controls.Add(language);language.SelectedIndex=1;
        title=LabelAt("",35,78,640,75,23,true);subtitle=LabelAt("",35,158,640,60,10,false);
        mode=new ComboBox(){DropDownStyle=ComboBoxStyle.DropDownList,Location=new Point(38,265),Size=new Size(630,35)};body.Controls.Add(mode);
        path=new TextBox(){Text=destination,Location=new Point(38,350),Size=new Size(515,30),RightToLeft=RightToLeft.No};body.Controls.Add(path);
        browse=ButtonAt("",563,345,105);browse.Click+=(s,e)=>{using(var f=new FolderBrowserDialog()){f.SelectedPath=path.Text;if(f.ShowDialog()==DialogResult.OK)path.Text=f.SelectedPath;}};
        next=ButtonAt("",510,555,160);next.BackColor=teal;next.ForeColor=Color.White;next.Click+=Next;
        back=ButtonAt("",38,555,110);back.Click+=(s,e)=>{stage=Math.Max(0,stage-1);RefreshView();};
        launch=new CheckBox(){Location=new Point(38,480),Size=new Size(630,30),Checked=true};body.Controls.Add(launch);
        log=new RichTextBox(){Location=new Point(38,250),Size=new Size(630,235),ReadOnly=true,BackColor=dark,ForeColor=Color.FromArgb(188,222,207),BorderStyle=BorderStyle.None,Font=new Font("Consolas",9),RightToLeft=RightToLeft.No};body.Controls.Add(log);
        progress=new ProgressBar(){Location=new Point(38,505),Size=new Size(630,8),Style=ProgressBarStyle.Continuous};body.Controls.Add(progress);
        language.SelectedIndexChanged+=(s,e)=>RefreshView();FormClosing+=(s,e)=>{if(stage==2)e.Cancel=true;};
        RefreshView();
    }
    void RefreshView(){
        bool rtl=Lang!=0;body.RightToLeft=rtl?RightToLeft.Yes:RightToLeft.No;steps.Text=T(21);steps.RightToLeft=rtl?RightToLeft.Yes:RightToLeft.No;
        // Retain the selected maintenance operation across language changes.
        int mi=mode.SelectedIndex;if(mi<0)mi=Array.IndexOf(new[]{"install","repair","update","uninstall"},initialMode);if(mi<0)mi=0;
        mode.Items.Clear();mode.Items.AddRange(new object[]{T(3),T(4),T(5),T(6)});mode.SelectedIndex=mi;
        foreach(Control c in body.Controls.OfType<Label>().ToArray())if(c!=title&&c!=subtitle)body.Controls.Remove(c);
        title.Text=T(stage==0?0:stage==1?17:stage==2?12:13);subtitle.Text=T(stage==0?1:stage==1?18:stage==2?16:22);
        mode.Visible=path.Visible=browse.Visible=stage<2;launch.Visible=stage==3&&mi!=3;launch.Text=T(15);
        log.Visible=progress.Visible=stage>=2;back.Visible=stage==1;next.Enabled=stage!=2;language.Enabled=stage<2;
        next.Text=T(stage==0?9:stage==1?11:14);back.Text=T(10);browse.Text=T(8);
        if(stage<2){LabelAt(T(2),38,230,630,28,10,true);LabelAt(T(7),38,315,630,28,10,true);LabelAt(T(16),38,400,630,75,10,false);LabelAt(T(22),38,477,630,64,9,false);}
        if(stage==3){log.Height=190;launch.Top=455;progress.Top=500;}
    }
    async void Next(object sender,EventArgs e){
        if(stage==0){stage=1;RefreshView();return;}
        if(stage==3){if(launch.Checked&&launch.Visible){try{Process.Start(Path.Combine(path.Text,Program.Exe));}catch(Exception ex){MessageBox.Show(ex.Message);}}Close();return;}
        string operation=new[]{"install","repair","update","uninstall"}[mode.SelectedIndex];
        if(operation=="uninstall"&&MessageBox.Show(T(6)+"?\n"+T(16),"Cable Label Studio",MessageBoxButtons.YesNo,MessageBoxIcon.Question)!=DialogResult.Yes)return;
        stage=2;RefreshView();
        try{
            string destination=path.Text;
            await Task.Run(()=>new Engine(destination,operation,true,true,
                message=>BeginInvoke((Action)(()=>{log.AppendText(message+Environment.NewLine);log.ScrollToCaret();})),
                value=>BeginInvoke((Action)(()=>progress.Value=Math.Max(0,Math.Min(100,value))))).Run());
            stage=3;RefreshView();
        }catch(Exception ex){stage=3;RefreshView();title.Text=T(19);launch.Visible=false;log.AppendText(ex+Environment.NewLine);}
    }
}
