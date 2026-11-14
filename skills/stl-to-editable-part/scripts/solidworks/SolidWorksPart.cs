using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Web.Script.Serialization;
using SolidWorks.Interop.sldworks;
using SolidWorks.Interop.swconst;
using SolidWorks.Interop.fworks;

public static class SolidWorksPart {
    public class Plan {
        public PlanFeature[] features { get; set; }
    }
    public class PlanFeature {
        public string name { get; set; }
        public int axis { get; set; }
        public double low { get; set; }
        public double high { get; set; }
        public bool cut { get; set; }
        public double[][][] polygons { get; set; }
        public double[][] circles { get; set; }
    }

    static void Log(string s) { Console.WriteLine(s); Console.Out.Flush(); }
    static void CloseTaskDocument(ISldWorks app, IModelDoc2 document) {
        string title=String.Empty;
        try {
            title=document.GetTitle();
            app.CloseDoc(title);
        } catch(COMException error) {
            Log("SolidWorks reported a document-close error for " + title + ": " + error.Message);
            if(String.IsNullOrEmpty(title)) throw;
            // Some sessions report an RPC error after completing CloseDoc.
            if(ArrayOf(app.GetDocuments()).Cast<IModelDoc2>().Any(d=>d.GetTitle()==title))
                throw;
        }
    }
    static object[] ArrayOf(object source) { return (source as object[]) ?? new object[0]; }
    static ISldWorks Connect() {
        ISldWorks app;
        try { app = (ISldWorks)Marshal.GetActiveObject("SldWorks.Application"); }
        catch (COMException) { app = (ISldWorks)Activator.CreateInstance(Type.GetTypeFromProgID("SldWorks.Application")); }
        Log("SOLIDWORKS " + app.RevisionNumber() + " PID " + app.GetProcessID() + " documents " + app.GetDocumentCount());
        return app;
    }
    static IEnumerable<IFeature> Tree(IModelDoc2 model) {
        for (IFeature f = model.FirstFeature() as IFeature; f != null; f = f.GetNextFeature() as IFeature) {
            yield return f;
            foreach (var sub in Children(f)) yield return sub;
        }
    }
    static IEnumerable<IFeature> Children(IFeature feature) {
        for (IFeature f = feature.GetFirstSubFeature() as IFeature; f != null; f = f.GetNextSubFeature() as IFeature) {
            yield return f;
            foreach (var sub in Children(f)) yield return sub;
        }
    }
    static void Audit(IModelDoc2 model) {
        foreach (var f in Tree(model)) {
            string type = f.GetTypeName2();
            string line = f.Name + " [" + type + "]";
            if (type == "ProfileFeature" || type == "3DProfileFeature") {
                var sketch = (ISketch)f.GetSpecificFeature2();
                var rels = ArrayOf(sketch.RelationManager.GetRelations(0));
                int fix = rels.Cast<ISketchRelation>().Count(r => new int[]{17,70,74}.Contains(r.GetRelationType()));
                int dims = 0, driving = 0;
                var drivingNames = new List<string>();
                for (var d = f.GetFirstDisplayDimension() as IDisplayDimension; d != null; d = f.GetNextDisplayDimension(d) as IDisplayDimension) {
                    dims++;
                    if (d.GetDimension2(0).DrivenState==(int)swDimensionDrivenState_e.swDimensionDriving) {
                        driving++;
                        drivingNames.Add(d.GetNameForSelection());
                    }
                }
                var owner = f.GetOwnerFeature() as IFeature;
                line += " sketch_status=" + sketch.GetConstrainedStatus() + " dims=" + dims + " driving=" + driving + " fix=" + fix + " owner=" + (owner==null ? "-" : owner.Name) + " driving_names=" + String.Join(",",drivingNames);
            }
            Log(line);
        }
        var bodies = ArrayOf(((IPartDoc)model).GetBodies2(0,false));
        Log("solid_count=" + bodies.Length);
        foreach (IBody2 body in bodies) {
            Log("body_check=" + body.Check2() + " faces=" + body.GetFaceCount());
            double[] extrema = new double[6];
            for (int i=0; i<6; i++) {
                var axis=new double[3]; axis[i%3] = i<3 ? -1 : 1;
                double x,y,z;
                if (!body.GetExtremePoint(axis[0],axis[1],axis[2],out x,out y,out z)) throw new Exception("Cannot read exact bounds");
                extrema[i] = new double[]{x,y,z}[i%3]*1000;
            }
            Log("bounds_mm=" + String.Join(",",extrema));
            foreach (IFace2 face in ArrayOf(body.GetFaces())) {
                var surface = (ISurface)face.GetSurface();
                if (!surface.IsCylinder()) continue;
                var p = (double[])surface.CylinderParams;
                Log("cylinder_axis_point_mm=" + (1000*p[0]) + "," + (1000*p[1]) + "," + (1000*p[2])
                    + " direction=" + p[3] + "," + p[4] + "," + p[5] + " diameter_mm=" + (2000*p[6]));
            }
        }
        if (bodies.Length > 0) Log("volume_mm3=" + (model.Extension.CreateMassProperty().Volume * 1e9));
    }
    static void DefineSketches(IModelDoc2 model) {
        var names = Tree(model).Where(f => f.GetTypeName2() == "ProfileFeature").Select(f => f.Name).Distinct().ToArray();
        string origin = Tree(model).First(f => f.GetTypeName2() == "OriginProfileFeature").Name;
        foreach (string name in names) {
            var feature = Tree(model).First(f => f.Name==name && f.GetTypeName2()=="ProfileFeature");
            var sketch = (ISketch)feature.GetSpecificFeature2();
            var oldFixes = ArrayOf(sketch.RelationManager.GetRelations(0)).Cast<ISketchRelation>()
                .Where(r => new[]{17,70,74}.Contains(r.GetRelationType())).ToArray();
            if (sketch.GetConstrainedStatus()==3 && oldFixes.Length==0) continue;
            model.ClearSelection2(true);
            if (!feature.Select2(false,0)) throw new Exception("Sketch could not be selected " + name);
            model.EditSketch();
            var active = (ISketch)model.SketchManager.ActiveSketch;
            if (active == null) throw new Exception("Sketch edit failed " + name);
            try {
                foreach (var relation in ArrayOf(active.RelationManager.GetRelations(0)).Cast<ISketchRelation>().Where(r => new[]{17,70,74}.Contains(r.GetRelationType())).ToArray()) {
                    if (!active.RelationManager.DeleteRelation((SketchRelation)relation))
                        throw new Exception("Could not replace fixed relation in " + name);
                }
                model.ClearSelection2(true);
                bool selected = false;
                foreach (string point in new[]{"Point1","点1"}) {
                    selected = model.Extension.SelectByID2(point + "@" + origin,"EXTSKETCHPOINT",0,0,0,false,6,null,0);
                    if (selected) break;
                }
                Log("Define " + name + " origin_selected=" + selected);
                var empty = new DispatchWrapper(null);
                int code = model.SketchManager.FullyDefineSketch(true,true,1023,true,1,empty,1,empty,1,1);
                Log("FullyDefineSketch=" + code + " status=" + active.GetConstrainedStatus());
            } finally {
                model.ClearSelection2(true);
                model.SketchManager.InsertSketch(true);
            }
        }
    }
    static double[] P(double x, double y, double z) { return new[]{x,y,z}; }
    static double[] Local(IMathUtility math, ISketch sketch, double[] world) {
        var point=(IMathPoint)math.CreatePoint(world.Select(v=>v/1000).ToArray());
        return (double[])((IMathPoint)point.MultiplyTransform(sketch.ModelToSketchTransform)).ArrayData;
    }
    static double[] Normal(IMathUtility math, ISketch sketch) {
        var vector=(IMathVector)math.CreateVector(P(0,0,1));
        return (double[])((IMathVector)vector.MultiplyTransform(sketch.ModelToSketchTransform.Inverse())).ArrayData;
    }
    static IFeature Plane(IModelDoc2 model, int axis) {
        string[] names = axis==0 ? new[]{"右视基准面","Right Plane"} :
            axis==1 ? new[]{"上视基准面","Top Plane"} : new[]{"前视基准面","Front Plane"};
        return Tree(model).First(f=>f.GetTypeName2()=="RefPlane" && names.Contains(f.Name));
    }
    static void BuildExtrusion(IModelDoc2 model, IMathUtility math, string label, int axis,
            double low, double high, bool cut, double[][][] polygons, double[][] circles) {
        model.ClearSelection2(true);
        if(!Plane(model,axis).Select2(false,0)) throw new Exception("Cannot select base plane for " + label);
        model.SketchManager.InsertSketch(true);
        var sketch=(ISketch)model.SketchManager.ActiveSketch;
        if(sketch==null) throw new Exception("Cannot start sketch " + label);
        var normal=Normal(math,sketch);
        if(Math.Abs(normal[axis])<0.999999) throw new Exception("Wrong sketch plane " + label);
        model.SketchManager.AddToDB=true;
        try {
            foreach(var polygon in polygons) {
                var lines = new List<ISketchLine>();
                var points = polygon.Select(point=>Local(math,sketch,point)).ToArray();
                for(int i=0;i<points.Length;i++) {
                    var a=points[i]; var b=points[(i+1)%points.Length];
                    var segment=model.SketchManager.CreateLine(a[0],a[1],0,b[0],b[1],0);
                    if(segment==null) throw new Exception("Could not create line " + label);
                    lines.Add((ISketchLine)segment);
                }
                for(int i=0;i<lines.Count;i++) {
                    var end=lines[i].GetEndPoint2();
                    var nextStart=lines[(i+1)%lines.Count].GetStartPoint2();
                    if (Object.ReferenceEquals(end,nextStart)) continue;
                    model.ClearSelection2(true);
                    if (!((ISketchPoint)end).Select4(false,null) || !((ISketchPoint)nextStart).Select4(true,null))
                        throw new Exception("Could not select adjoining endpoints " + label);
                    model.SketchAddConstraints("sgMERGEPOINTS");
                }
            }
            foreach(var circle in circles) {
                var p=Local(math,sketch,P(circle[0],circle[1],circle[2]));
                if(model.SketchManager.CreateCircleByRadius(p[0],p[1],0,circle[3]/1000)==null)
                    throw new Exception("Could not create circle " + label);
            }
        } finally { model.SketchManager.AddToDB=false; }
        string origin=Tree(model).First(f=>f.GetTypeName2()=="OriginProfileFeature").Name;
        model.ClearSelection2(true);
        foreach(string point in new[]{"Point1","点1"}) {
            if(model.Extension.SelectByID2(point+"@"+origin,"EXTSKETCHPOINT",0,0,0,false,6,null,0)) break;
        }
        var empty=new DispatchWrapper(null);
        int defined=model.SketchManager.FullyDefineSketch(true,true,1023,true,1,empty,1,empty,1,1);
        int state=sketch.GetConstrainedStatus();
        Log(label + " define code=" + defined + " state=" + state);
        if(state!=3) throw new Exception("Sketch not fully defined for " + label);
        var profile=(IFeature)sketch;
        model.ClearSelection2(true);
        model.SketchManager.InsertSketch(true);
        profile.Name=label+"草图";
        if(!profile.Select2(false,0)) throw new Exception("Cannot select generated profile " + label);
        bool reversed = cut ? normal[axis]>0 : normal[axis]<0;
        double depth = (high-low)/1000;
        double start = low/1000*normal[axis];
        int startMode = Math.Abs(start)>1e-12 ? 3 : 0;
        IFeature feature;
        if(cut) {
            feature=model.FeatureManager.FeatureCut4(true,false,reversed,0,0,depth,0,
                false,false,false,false,0,0,false,false,false,false,false,true,true,false,false,false,
                startMode,Math.Abs(start),start<0,false);
        } else {
            feature=model.FeatureManager.FeatureExtrusion3(true,false,reversed,0,0,depth,0,
                false,false,false,false,0,0,false,false,false,false,true,false,true,
                startMode,Math.Abs(start),start<0);
        }
        if(feature==null) throw new Exception("Feature creation failed: "+label+" normal="+normal[axis]+" start="+start);
        feature.Name=label;
        Log("Created " + label + " type=" + feature.GetTypeName2() + " error=" + feature.GetErrorCode());
        if(feature.GetErrorCode()!=0) throw new Exception("Feature reports a rebuild error: " + label);
        var bodies=ArrayOf(((IPartDoc)model).GetBodies2(0,false));
        Log("Feature solids=" + bodies.Length + " volume_mm3=" + model.Extension.CreateMassProperty().Volume*1e9);
        if(bodies.Length!=1) throw new Exception("Unexpected number of solids after " + label);
    }

    static bool IsFinite(double value) {
        return !Double.IsNaN(value) && !Double.IsInfinity(value);
    }

    static void CheckPoint(double[] point, int size, int axis) {
        if (point==null || point.Length!=size || point.Any(value=>!IsFinite(value)) || Math.Abs(point[axis])>1e-7)
            throw new ArgumentException("Sketch coordinates must lie on the chosen base plane, in mm");
    }

    static void SavePart(IModelDoc2 model, string destination) {
        if (File.Exists(destination)) throw new IOException("Destination already exists: " + destination);
        int errors=0, warnings=0;
        bool saved=model.Extension.SaveAs(destination,0,1,null,ref errors,ref warnings);
        Log("SaveAs=" + saved + " errors=" + errors + " warnings=" + warnings);
        if (!saved || errors!=0 || !File.Exists(destination) || new FileInfo(destination).Length==0)
            throw new IOException("SLDPRT save failed");
    }

    static void RebuildFromPlan(ISldWorks app, string source, string destination, string template) {
        var plan=new JavaScriptSerializer().Deserialize<Plan>(File.ReadAllText(source));
        if(plan==null || plan.features==null || plan.features.Length==0 || plan.features.Any(f=>f==null) || plan.features[0].cut)
            throw new ArgumentException("The plan needs at least one feature, starting with a boss extrusion");
        var names=new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        foreach(var feature in plan.features) {
            if(String.IsNullOrWhiteSpace(feature.name) || !names.Add(feature.name))
                throw new ArgumentException("Use unique, non-empty feature names");
            if(feature.axis<0 || feature.axis>2 || !IsFinite(feature.low) || !IsFinite(feature.high) || feature.high<=feature.low)
                throw new ArgumentException("A feature must have a valid axis and high > low");
            feature.polygons=feature.polygons ?? new double[0][][];
            feature.circles=feature.circles ?? new double[0][];
            if(feature.polygons.Length+feature.circles.Length==0)
                throw new ArgumentException("A feature must have at least one sketch contour");
            foreach(var polygon in feature.polygons) {
                if(polygon==null || polygon.Length<3) throw new ArgumentException("A polygon needs three or more vertices");
                foreach(var point in polygon) CheckPoint(point,3,feature.axis);
            }
            foreach(var circle in feature.circles) {
                CheckPoint(circle,4,feature.axis);
                if(circle[3]<=0) throw new ArgumentException("Circle radius must be positive");
            }
        }
        if(String.IsNullOrWhiteSpace(template)) {
            template=app.GetUserPreferenceStringValue((int)swUserPreferenceStringValue_e.swDefaultTemplatePart);
            if(!File.Exists(template)) template=app.GetDocumentTemplate(1,"",0,0,0);
        }
        if(!File.Exists(template)) throw new ArgumentException("Set -Template to a valid SolidWorks .prtdot");
        var model=(IModelDoc2)app.NewDocument(template,0,0,0);
        if(model==null) throw new InvalidOperationException("Could not open the part template");
        try {
            var math=(IMathUtility)app.GetMathUtility();
            foreach(var feature in plan.features)
                BuildExtrusion(model,math,feature.name,feature.axis,feature.low,feature.high,feature.cut,feature.polygons,feature.circles);
            CheckEditable(model);
            model.ClearSelection2(true);
            model.ShowNamedView2("",7);
            model.ViewZoomtofit2();
            Audit(model);
            SavePart(model,destination);
        } finally { CloseTaskDocument(app,model); }
    }

    static IBody2 OneSolid(IModelDoc2 model) {
        var solidBodies=ArrayOf(((IPartDoc)model).GetBodies2(0,false));
        var surfaceBodies=ArrayOf(((IPartDoc)model).GetBodies2(1,false));
        if(solidBodies.Length!=1 || surfaceBodies.Length!=0)
            throw new InvalidOperationException("Expected one closed solid and no surface bodies");
        var body=(IBody2)solidBodies[0];
        if(body.Check2()!=0) throw new InvalidOperationException("Solid body check failed");
        return body;
    }

    static IFeature[] Sketches(IModelDoc2 model) {
        return Tree(model).Where(f=>f.GetTypeName2()=="ProfileFeature" || f.GetTypeName2()=="3DProfileFeature")
            .GroupBy(f=>f.Name).Select(group=>group.First()).ToArray();
    }

    static IEnumerable<IDisplayDimension> Dimensions(IFeature feature) {
        for(var display=feature.GetFirstDisplayDimension() as IDisplayDimension;display!=null;display=feature.GetNextDisplayDimension(display) as IDisplayDimension)
            yield return display;
    }

    static bool IsDriving(IDisplayDimension display) {
        return display.GetDimension2(0).DrivenState==(int)swDimensionDrivenState_e.swDimensionDriving;
    }

    static void CheckSketches(IModelDoc2 model) {
        var sketches=Sketches(model);
        if(sketches.Length==0) throw new InvalidOperationException("No editable modeling sketches");
        foreach(var feature in sketches) {
            var sketch=(ISketch)feature.GetSpecificFeature2();
            if(sketch.GetConstrainedStatus()!=3) throw new InvalidOperationException("Sketch not fully defined: " + feature.Name);
            if(ArrayOf(sketch.RelationManager.GetRelations(0)).Cast<ISketchRelation>().Any(r=>new[]{17,70,74}.Contains(r.GetRelationType())))
                throw new InvalidOperationException("Fixed relation remains: " + feature.Name);
            if(!Dimensions(feature).Any(IsDriving)) throw new InvalidOperationException("No driving dimensions: " + feature.Name);
            var owner=feature.GetOwnerFeature() as IFeature;
            var consumers=(owner==null ? ArrayOf(feature.GetChildren()).Cast<IFeature>() : new[]{owner})
                .Where(f=>f.GetTypeName2()!="ProfileFeature" && f.GetTypeName2()!="3DProfileFeature" && !f.IsSuppressed()).ToArray();
            if(consumers.Length==0) throw new InvalidOperationException("Sketch has no active consumer: " + feature.Name);
            if(consumers.Any(f=>f.GetErrorCode()!=0)) throw new InvalidOperationException("Sketch feature failed to rebuild: " + feature.Name);
        }
        Log("Verified fully defined sketches=" + sketches.Length);
    }

    static void CheckEditable(IModelDoc2 model) {
        if(!model.ForceRebuild3(false)) throw new InvalidOperationException("SolidWorks rebuild failed");
        if(Tree(model).Any(f=>f.Is3DInterconnectFeature || (!f.IsSuppressed() && IsImported(f))))
            throw new InvalidOperationException("An imported solid or 3D Interconnect link remains");
        OneSolid(model);
        CheckSketches(model);
    }

    static bool IsImported(IFeature feature) {
        string type=feature.GetTypeName2();
        return type=="BaseBody" || type=="MBimport" || type=="Imported";
    }

    static double Volume(IModelDoc2 model) {
        return model.Extension.CreateMassProperty().Volume*1e9;
    }

    static double[] Bounds(IBody2 body) {
        var bounds=new double[6];
        for(int i=0; i<bounds.Length; i++) {
            var axis=new double[3];
            axis[i%3]=i<3 ? -1 : 1;
            double x,y,z;
            if(!body.GetExtremePoint(axis[0],axis[1],axis[2],out x,out y,out z))
                throw new InvalidOperationException("Could not measure body bounds");
            bounds[i]=new[]{x,y,z}[i%3]*1000;
        }
        return bounds;
    }

    static void CompareBodies(IModelDoc2 result, IModelDoc2 baseline, double volumeTolerance, double boundsTolerance) {
        IBody2 first=OneSolid(result), second=OneSolid(baseline);
        double volumeDelta=Math.Abs(Volume(result)-Volume(baseline));
        double boundsDelta=Bounds(first).Zip(Bounds(second),(a,b)=>Math.Abs(a-b)).Max();
        Log("Volume delta mm3=" + volumeDelta + " max bounds delta mm=" + boundsDelta);
        if(volumeDelta>volumeTolerance || boundsDelta>boundsTolerance)
            throw new InvalidOperationException("Solid does not match the geometric baseline");
        foreach(var pair in new[]{new[]{first,second},new[]{second,first}}) {
            int error;
            var copy=(IBody2)pair[0].Copy();
            var other=(IBody2)pair[1].Copy();
            var difference=ArrayOf(copy.Operations2((int)swBodyOperationType_e.SWBODYCUT,other,out error));
            if(error!=0 && error!=(int)swBodyOperationError_e.swBodyOperationEmptyBody)
                throw new InvalidOperationException("Boolean comparison failed: " + error);
            double residual=difference.Cast<IBody2>().Sum(body=>Math.Abs(((double[])body.GetMassProperties(1.0))[3])*1e9);
            Log("Boolean difference fragments=" + difference.Length + " residual mm3=" + residual);
            if(residual>volumeTolerance) throw new InvalidOperationException("Geometric difference exceeds tolerance");
        }
    }

    static bool TryDimension(IModelDoc2 model, IDisplayDimension display, double factor) {
        string name=display.GetNameForSelection();
        var dimension=(IDimension)display.GetDimension2(0);
        double oldValue=((double[])dimension.GetSystemValue3(1,null))[0];
        if(oldValue==0) return false;
        double oldVolume=Volume(model);
        try {
            if(dimension.SetSystemValue3(oldValue*factor,1,null)!=0 || !model.ForceRebuild3(false))
                return false;
            OneSolid(model);
            CheckSketches(model);
            double delta=Math.Abs(Volume(model)-oldVolume);
            if(delta<=1e-6) return false;
            Log("Edit verified " + name + ", absolute volume change mm3=" + delta);
            return true;
        } catch(InvalidOperationException) {
            return false;
        } finally {
            if(dimension.SetSystemValue3(oldValue,1,null)!=0 || !model.ForceRebuild3(false))
                throw new InvalidOperationException("Scratch edit could not be restored");
        }
    }

    static void TestDimension(IModelDoc2 model, string name, double factor) {
        var names=Sketches(model).Reverse().SelectMany(Dimensions).Where(IsDriving)
            .Select(d=>d.GetNameForSelection()).Distinct().ToArray();
        if(name!="__auto__") {
            names=names.Where(n=>String.Equals(n,name,StringComparison.OrdinalIgnoreCase)).ToArray();
            if(names.Length==0)
                throw new InvalidOperationException("Driving dimension not found: " + name + ". Use Audit to list dimension names.");
        }
        foreach(string candidate in names.Take(8)) {
            var display=Sketches(model).SelectMany(Dimensions)
                .First(d=>String.Equals(d.GetNameForSelection(),candidate,StringComparison.OrdinalIgnoreCase));
            if(TryDimension(model,display,factor)) {
                CheckEditable(model);
                return;
            }
            Log("No valid solid change from edit test: " + candidate);
        }
        throw new InvalidOperationException("No tested dimension produced a valid solid change. Choose a representative driver with -EditDimension.");
    }

    static void Preview(ISldWorks app, IModelDoc2 model, string path) {
        bool wasVisible=app.Visible;
        try {
            app.Visible=true;
            Activate(app,model);
            model.ClearSelection2(true);
            model.ShowNamedView2("",7);
            model.ViewZoomtofit2();
            model.GraphicsRedraw2();
            if(!model.SaveBMP(path,1100,800) || !File.Exists(path))
                throw new IOException("Could not save validation preview");
        } finally { app.Visible=wasVisible; }
    }

    static void Activate(ISldWorks app,IModelDoc2 model) {
        int error=0;
        app.ActivateDoc3(model.GetTitle(),false,0,ref error);
        var active=(IModelDoc2)app.ActiveDoc;
        if(active==null || !Object.ReferenceEquals(active,model))
            throw new InvalidOperationException("Could not activate the task document: " + model.GetTitle());
    }

    static IModelDoc2 Open(ISldWorks app,string path,bool allowStep) {
        if(app.GetOpenDocumentByName(path)!=null) throw new InvalidOperationException("Use a closed working copy: " + path);
        int error=0, warning=0;
        IModelDoc2 model=null;
        bool part=path.EndsWith(".sldprt",StringComparison.OrdinalIgnoreCase);
        if(part) {
            model=app.OpenDoc6(path,1,3,"",ref error,ref warning);
            Log("SLDPRT open error=" + error + " warnings=" + warning);
        } else if(allowStep) {
            var data=app.GetImportFileData(path);
            model=app.LoadFile4(path,"r",data,ref error);
            Log("STEP LoadFile4 error=" + error);
            if(model==null) {
                var spec=(IDocumentSpecification)app.GetOpenDocSpec(path);
                spec.Silent=true;
                model=app.OpenDoc7(spec);
                error=spec.Error;
                Log("STEP OpenDoc7 error=" + error);
            }
        }
        if(model==null) throw new InvalidOperationException("Could not open part. If STEP API import failed, use the desktop to save an imported SLDPRT copy.");
        if(part && !String.Equals(Path.GetFullPath(model.GetPathName()),path,StringComparison.OrdinalIgnoreCase))
            throw new InvalidOperationException("SolidWorks returned an already open document with a different path");
        if(model.GetType()!=1 || error!=0) {
            app.CloseDoc(model.GetTitle());
            throw new InvalidOperationException("Source did not open as a valid SolidWorks part");
        }
        return model;
    }

    static IFeatureWorksApp FeatureWorks(ISldWorks app,string dll) {
        var featureWorks=app.GetAddInObject("FeatureWorks.FeatureWorksApp") as IFeatureWorksApp;
        if(featureWorks==null && File.Exists(dll)) {
            int result=app.LoadAddIn(dll);
            Log("FeatureWorks LoadAddIn=" + result);
            featureWorks=app.GetAddInObject("FeatureWorks.FeatureWorksApp") as IFeatureWorksApp;
        }
        Log("FeatureWorks API available=" + (featureWorks!=null));
        return featureWorks;
    }

    public static void Run(string mode,string source,string destination,string baseline,string template,string fwDll,
        int recognitionOptions,double volumeTolerance,double boundsTolerance,string editDimension,double editFactor,string preview) {
        var app=Connect();
        if(mode=="Probe") { FeatureWorks(app,fwDll); return; }
        if(mode=="Rebuild") { RebuildFromPlan(app,source,destination,template); return; }
        var model=Open(app,source,mode=="Prepare");
        try {
            Activate(app,model);
            switch(mode) {
                case "Prepare":
                    OneSolid(model);
                    foreach(var feature in Tree(model).Where(f=>f.Is3DInterconnectFeature).ToArray()) {
                        int result=feature.BreakLink(false,true);
                        Log("BreakLink=" + result);
                        if(result!=0) throw new InvalidOperationException("Could not detach copied imported solid");
                    }
                    if(Tree(model).Any(f=>f.Is3DInterconnectFeature) || !Tree(model).Any(IsImported))
                        throw new InvalidOperationException("Independent import feature was not created");
                    OneSolid(model);
                    Audit(model);
                    SavePart(model,destination);
                    break;
                case "Recognize":
                    OneSolid(model);
                    if(Tree(model).Any(f=>f.Is3DInterconnectFeature))
                        throw new InvalidOperationException("Prepare a detached imported solid before recognition");
                    var imported=Tree(model).FirstOrDefault(IsImported);
                    if(imported==null) throw new InvalidOperationException("No imported base feature to recognize");
                    var fw=FeatureWorks(app,fwDll);
                    if(fw==null) throw new InvalidOperationException("FeatureWorks add-in is unavailable");
                    model.ClearSelection2(true);
                    if(!imported.Select2(false,0)) throw new InvalidOperationException("Cannot select imported feature");
                    int recognized=fw.RecognizeFeatureAutomatic(recognitionOptions);
                    Log("RecognizeFeatureAutomatic=" + recognized);
                    if(!fw.CreateFeatures(0)) throw new InvalidOperationException("FeatureWorks did not create features. Check the desktop recognition dialog.");
                    var recognizedModel=(IModelDoc2)app.ActiveDoc;
                    if(recognizedModel==null || !Object.ReferenceEquals(recognizedModel,model))
                        throw new InvalidOperationException("Recognition switched documents. Review and save the new task part in SolidWorks.");
                    if(!model.ForceRebuild3(false) || Sketches(model).Length==0)
                        throw new InvalidOperationException("Recognition did not produce rebuildable sketch features");
                    OneSolid(model);
                    Audit(model);
                    SavePart(model,destination);
                    break;
                case "Define":
                    DefineSketches(model);
                    CheckEditable(model);
                    Audit(model);
                    SavePart(model,destination);
                    break;
                case "Audit":
                    Audit(model);
                    break;
                case "Validate":
                    CheckEditable(model);
                    var reference=Open(app,baseline,false);
                    try { CompareBodies(model,reference,volumeTolerance,boundsTolerance); }
                    finally { CloseTaskDocument(app,reference); }
                    Activate(app,model);
                    if(!String.IsNullOrWhiteSpace(editDimension)) TestDimension(model,editDimension,editFactor);
                    if(!String.IsNullOrWhiteSpace(preview)) Preview(app,model,preview);
                    Audit(model);
                    break;
            }
        } finally { CloseTaskDocument(app,model); }
    }
}
