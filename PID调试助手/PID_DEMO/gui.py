#!/usr/bin/env python3
"""MSPM0G3507 PID 调参工具 — 中文 GUI"""

import sys, os, json, threading, queue, time, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

from mspm0g_tuner.config import load_config, DEFAULT_CONFIG

# ═══ 设计系统 ═══
C = {"bg":"#f3f4f6","card":"#fff","hover":"#e5e7eb","border":"#d1d5db",
     "text":"#111827","sub":"#6b7280","muted":"#9ca3af",
     "accent":"#4f46e5","green":"#059669","red":"#dc2626","amber":"#d97706","blue":"#2563eb","pink":"#c026d3"}
F = {"b":("Microsoft YaHei UI",10),"m":("Consolas",10),"h":("Microsoft YaHei UI",12,"bold"),
     "big":("Consolas",22,"bold"),"s":("Microsoft YaHei UI",9),"title":("Microsoft YaHei UI",14,"bold")}

def _card(p,**kw):
    return tk.Frame(p,bg=C["card"],highlightbackground=C["border"],highlightthickness=1,padx=12,pady=10,**kw)
def _btn(p,text,cmd,pri=False):
    bg=C["accent"] if pri else C["card"];fg="white" if pri else C["text"]
    b=tk.Button(p,text=f" {text} ",command=cmd,font=("Microsoft YaHei UI",10),bg=bg,fg=fg,
                activebackground="#4338ca" if pri else C["hover"],
                activeforeground="white" if pri else C["text"],
                relief=tk.FLAT,bd=0 if pri else 1,padx=16,pady=7,cursor="hand2",
                highlightbackground=C["border"] if not pri else bg,highlightthickness=0)
    return b
def _lbl(p,text,font=None,fg=None,**kw):
    return tk.Label(p,text=text,font=font or F["b"],fg=fg or C["text"],bg=p.cget("bg"),**kw)
def _ent(p,default,w=8):
    e=tk.Entry(p,font=F["b"],fg=C["text"],bg=C["bg"],relief=tk.FLAT,width=w,
               highlightbackground=C["border"],highlightthickness=1,insertbackground=C["accent"])
    e.insert(0,str(default));e.pack(ipady=3);return e

# ═══ 实时曲线 ═══
class Curve(tk.Canvas):
    def __init__(self,p,h=240):
        super().__init__(p,height=h,bg="white",highlightthickness=1,highlightbackground=C["border"],bd=0)
        self.H=h;self.data=[];self.target=60;self.max_pts=200;self.max_y=120
        self.bind("<Configure>",lambda e:self.draw())
    def add(self,v,t=None):
        if t is not None:self.target=t
        self.data.append(v)
        if len(self.data)>self.max_pts:self.data.pop(0)
        self.draw()
    def _axes(self,w,h):
        M=40;R=12;B=28  # margins: left, right, bottom
        pw=w-M-R;ph=h-B-20
        if pw<10:return M,R,B,pw,ph
        # grid + y-axis
        n_ticks=4
        for i in range(n_ticks+1):
            y=B+ph-ph*i/n_ticks;val=self.max_y*i/n_ticks
            self.create_line(M,y,w-R,y,fill="#f0f0f0",dash=(2,4) if i>0 else None,width=1)
            self.create_text(M-4,y,text=f"{val:.0f}",font=("Consolas",8),fill=C["sub"],anchor=tk.E)
        # x-axis
        self.create_line(M,B,w-R,B,fill=C["border"])
        self.create_text(w//2,B+16,text="采样点",font=F["s"],fill=C["sub"],anchor=tk.N)
        # y-axis label
        self.create_text(8,h//2,text="速度",font=F["s"],fill=C["sub"],anchor=tk.S,angle=90)
        return M,R,B,pw,ph
    def draw(self):
        self.delete("all");w=self.winfo_width();h=self.H
        if w<10:return
        M,R,B,pw,ph=self._axes(w,h)
        n=len(self.data)
        if n<2 or ph<1:return
        # target line
        ty=B+ph-ph*min(self.target,self.max_y)/self.max_y
        self.create_line(M,ty,w-R,ty,fill=C["red"],dash=(6,3),width=1.5,tags="curve")
        self.create_text(w-R,ty-8,text=f"目标={self.target:.0f}",font=("Consolas",8),fill=C["red"],anchor=tk.E,tags="curve")
        # speed curve
        pts=[]
        for i in range(n):
            x=M+pw*i/max(1,n-1);y=B+ph-ph*min(self.data[i],self.max_y)/self.max_y
            pts.extend([x,y])
        if len(pts)>=4:
            for i in range(0,len(pts)-2,2):
                self.create_line(pts[i],pts[i+1],pts[i+2],pts[i+3],fill=C["accent"],width=1.8,tags="curve")
        # last value
        if pts:
            lx=pts[-2];ly=pts[-1]
            self.create_oval(lx-4,ly-4,lx+4,ly+4,fill=C["accent"],outline="white",width=2,tags="curve")
            self.create_text(lx+10,ly-8,text=f"{self.data[-1]:.1f}",font=("Consolas",9,"bold"),fill=C["accent"],anchor=tk.W,tags="curve")
        # legend
        self.create_rectangle(M+6,6,M+80,22,fill="white",outline=C["border"],tags="curve")
        self.create_line(M+12,14,M+28,14,fill=C["accent"],width=2,tags="curve")
        self.create_text(M+44,14,text="速度",font=F["s"],fill=C["text"],anchor=tk.W,tags="curve")
        self.create_line(M+82,14,M+92,14,fill=C["red"],dash=(4,2),tags="curve")
        self.create_text(M+106,14,text="目标",font=F["s"],fill=C["red"],anchor=tk.W,tags="curve")
    def clear(self):self.data.clear();self.delete("all");self._axes(self.winfo_width(),self.H)

# ═══ 主应用 ═══
class App:
    def __init__(self,root):
        self.root=root;self.root.title("MSPM0G3507 PID 调参工具")
        self.root.geometry("1060x720");self.root.minsize(900,560)
        self.root.configure(bg=C["bg"])
        self.config=load_config("config.json") if os.path.exists("config.json") else dict(DEFAULT_CONFIG)
        self.running=False;self._stop_event=threading.Event();self.q=queue.Queue();self.pid={"p":5.0,"i":2.0,"d":0.0}
        self._bridge=None;self._conn=False;self.mode="auto"
        self._top_bar()
        self._layout()
        self._show_page("auto")
        self._poll()

    # ═══ 顶部串口栏 ═══
    def _top_bar(self):
        b=tk.Frame(self.root,bg=C["card"],height=42);b.pack(fill=tk.X);b.pack_propagate(False)
        _lbl(b,"MSPM0G3507 PID 调参",F["title"],C["accent"]).pack(side=tk.LEFT,padx=14,pady=8)
        _lbl(b,"端口",F["s"],C["sub"]).pack(side=tk.LEFT,padx=(20,4),pady=14)
        self._tb_port=ttk.Combobox(b,values=self._scan_ports(),width=9,font=F["b"])
        self._tb_port.set(self.config.get("SERIAL_PORT","AUTO"))
        self._tb_port.pack(side=tk.LEFT,ipady=0,pady=10)
        _btn(b,"刷新",lambda:self._tb_port.config(values=self._scan_ports())).pack(side=tk.LEFT,padx=(2,8),pady=8)
        _lbl(b,"波特率",F["s"],C["sub"]).pack(side=tk.LEFT,padx=(0,4),pady=14)
        self._tb_baud=_ent(b,str(self.config.get("BAUD_RATE",115200)),6)
        self._tb_baud.pack(side=tk.LEFT,ipady=1,pady=10)
        self._tb_cbtn=tk.Button(b,text="连接设备",font=F["b"],bg=C["accent"],fg="white",
                                activebackground="#4338ca",activeforeground="white",
                                relief=tk.FLAT,bd=0,padx=12,pady=4,cursor="hand2",command=self._conn_toggle)
        self._tb_cbtn.pack(side=tk.LEFT,padx=10,pady=8)
        self._tb_dot=tk.Label(b,text="●",font=("Consolas",9),fg=C["muted"],bg=C["card"])
        self._tb_dot.pack(side=tk.RIGHT,padx=(0,4),pady=12)
        self._tb_lbl=_lbl(b,"离线",F["s"],C["muted"])
        self._tb_lbl.pack(side=tk.RIGHT,padx=(0,14),pady=13)

    @staticmethod
    def _scan_ports():
        try:
            import serial.tools.list_ports
            ports=[p.device for p in serial.tools.list_ports.comports()]
            return ports if ports else ["AUTO","COM1","COM2","COM3","COM4","COM5","COM6"]
        except:return ["AUTO","COM1","COM2","COM3","COM4","COM5","COM6"]

    def _conn_toggle(self):
        if not self._conn:
            from mspm0g_tuner.bridge import SerialBridge
            try:baud=int(self._tb_baud.get())
            except:baud=115200
            port=self._tb_port.get().strip() or "AUTO"
            self._bridge=SerialBridge(port=port,baud=baud)
            if self._bridge.connect():
                self._conn=True
                self._tb_cbtn.config(text="● 已连接 — 点此断开",bg="#dcfce7",fg=C["green"],activebackground="#bbf7d0")
                self._tb_dot.config(fg=C["green"],font=("Consolas",14));self._tb_lbl.config(text="设备在线",fg=C["green"],font=F["b"])
            else:self._tb_dot.config(fg=C["red"])
        else:
            self._bridge.disconnect();self._conn=False
            self._tb_cbtn.config(text="连接设备",bg=C["accent"],fg="white",activebackground="#4338ca")
            self._tb_dot.config(fg=C["muted"]);self._tb_lbl.config(text="离线",fg=C["muted"])

    # ═══ 三栏布局 ═══
    def _layout(self):
        main=tk.Frame(self.root,bg=C["bg"]);main.pack(fill=tk.BOTH,expand=True)

        # ── 左侧: 设置选项 ──
        self._left=tk.Frame(main,bg=C["card"],width=150)
        self._left.pack(side=tk.LEFT,fill=tk.Y);self._left.pack_propagate(False)
        tk.Frame(self._left,bg=C["border"],height=1).pack(fill=tk.X,padx=10)

        _lbl(self._left,"设置选项",F["h"],C["text"]).pack(anchor=tk.W,padx=14,pady=(14,8))
        self._nav={}
        for mode,label in [("auto","自动调参"),("manual","手动配置"),("settings","LLM 设置")]:
            b=tk.Button(self._left,text=label,font=F["b"],fg=C["sub"],bg=C["card"],
                        activebackground="#eef2ff",activeforeground=C["accent"],
                        relief=tk.FLAT,bd=0,padx=14,pady=10,cursor="hand2",
                        anchor=tk.W,command=lambda m=mode:self._show_page(m))
            b.pack(fill=tk.X)
            self._nav[mode]=b
        tk.Frame(self._left,bg=C["border"],height=1).pack(fill=tk.X,padx=10,pady=8)

        _lbl(self._left,"连接设置",F["s"],C["muted"]).pack(anchor=tk.W,padx=14,pady=(4,4))
        _lbl(self._left,"端口号和波特率在顶部栏修改",F["s"],C["muted"],wraplength=120).pack(anchor=tk.W,padx=14)

        tk.Frame(self._left,bg=C["border"],height=1).pack(fill=tk.X,padx=10,pady=(16,4))
        _lbl(self._left,"v0.2",F["s"],C["muted"]).pack(side=tk.BOTTOM,anchor=tk.W,padx=14,pady=10)

        # ── 中间: 设置内容 ──
        self._center=tk.Frame(main,bg=C["bg"])

        # ── 右侧: PID 曲线 ──
        self._right=tk.Frame(main,bg=C["bg"],width=350)
        self._right.pack(side=tk.RIGHT,fill=tk.BOTH);self._right.pack_propagate(False)

        # 曲线卡片
        cf=_card(self._right);cf.pack(fill=tk.BOTH,expand=True,padx=(4,10),pady=(10,4))
        _lbl(cf,"实时曲线",F["b"],C["sub"]).pack(anchor=tk.W)
        self._curve=Curve(cf,280)
        self._curve.pack(fill=tk.BOTH,expand=True,pady=(4,0))

        # 评分卡
        sc=_card(self._right);sc.pack(fill=tk.X,padx=(4,10),pady=(0,4))
        _lbl(sc,"稳定性评分",F["s"],C["sub"]).pack(anchor=tk.W)
        self._score_var=tk.StringVar(value="--- %")
        tk.Label(sc,textvariable=self._score_var,font=("Consolas",30,"bold"),fg=C["accent"],bg=C["card"]).pack(anchor=tk.W)

        rc=_card(self._right);rc.pack(fill=tk.X,padx=(4,10),pady=(0,10))
        _lbl(rc,"推荐 PID",F["s"],C["sub"]).pack(anchor=tk.W)
        self._rec_var=tk.StringVar(value="---")
        tk.Label(rc,textvariable=self._rec_var,font=F["big"],fg=C["green"],bg=C["card"]).pack(anchor=tk.W)

        # 构建各页
        self._pages={}
        self._build_auto();self._build_manual();self._build_settings()

    def _show_page(self,mode):
        self.mode=mode
        for m,b in self._nav.items():
            sel=(m==mode)
            b.config(bg="#eef2ff" if sel else C["card"],fg=C["accent"] if sel else C["sub"])
        for p in self._pages.values():p.pack_forget()
        self._center.pack(side=tk.LEFT,fill=tk.BOTH,expand=True)
        self._pages[mode].pack(fill=tk.BOTH,expand=True,padx=(4,0),pady=(10,10))

    # ═══ 自动调参页面 ═══
    def _build_auto(self):
        pg=tk.Frame(self._center,bg=C["bg"]);self._pages["auto"]=pg

        bar=_card(pg);bar.pack(fill=tk.X,pady=(0,8))
        r=tk.Frame(bar,bg=C["card"]);r.pack(fill=tk.X)
        # 模式选择
        self._auto_mode=tk.StringVar(value="sim")
        _lbl(r,"模式:",F["b"],C["sub"]).pack(side=tk.LEFT,padx=(0,2))
        for mode,label in [("sim","仿真"),("hw","硬件")]:
            tk.Radiobutton(r,text=label,variable=self._auto_mode,value=mode,font=F["b"],
                          bg=C["card"],fg=C["text"],activebackground=C["card"],
                          selectcolor=C["card"],cursor="hand2",
                          command=lambda m=mode:self._mode_changed(m)).pack(side=tk.LEFT,padx=(0,8))
        tk.Frame(r,bg=C["border"],width=1).pack(side=tk.LEFT,fill=tk.Y,padx=6)
        # 算法/轮次/目标
        self._auto_algo=ttk.Combobox(r,values=["LLM 大模型","贝叶斯优化","Ziegler-Nichols","继电反馈法"],state="readonly",width=14,font=F["b"])
        self._auto_algo.set("LLM 大模型");self._auto_algo.pack(side=tk.LEFT,padx=(4,8))
        _lbl(r,"轮次:",F["b"],C["sub"]).pack(side=tk.LEFT,padx=(0,2))
        self._auto_rnd=_ent(r,15,4);self._auto_rnd.pack(side=tk.LEFT,padx=(0,8))
        _lbl(r,"目标:",F["b"],C["sub"]).pack(side=tk.LEFT,padx=(0,2))
        self._auto_tgt=_ent(r,60,4);self._auto_tgt.pack(side=tk.LEFT)
        _btn(r,"开始调参",self._auto_start,pri=True).pack(side=tk.RIGHT)
        # mode status
        self._auto_mode_lbl=_lbl(r,"",F["s"],C["muted"])
        self._auto_mode_lbl.pack(side=tk.RIGHT,padx=(0,10))

        # PID 卡片
        cd=tk.Frame(pg,bg=C["bg"]);cd.pack(fill=tk.X,pady=(0,8))
        self._av={}
        for lab,key,clr in [("Kp 比例","p",C["blue"]),("Ki 积分","i",C["red"]),("Kd 微分","d",C["amber"])]:
            c=_card(tk.Frame(cd,bg=C["bg"]));c.pack(side=tk.LEFT,padx=(0,6),fill=tk.X,expand=True)
            _lbl(c,lab,F["s"],C["sub"]).pack(anchor=tk.W)
            v=tk.StringVar(value="---")
            tk.Label(c,textvariable=v,font=F["big"],fg=clr,bg=C["card"]).pack(anchor=tk.W,pady=(1,0))
            self._av[key]=v

        # 决策日志
        lf=_card(pg);lf.pack(fill=tk.BOTH,expand=True)
        _lbl(lf,"决策日志",F["b"],C["sub"]).pack(anchor=tk.W)
        self._auto_log=scrolledtext.ScrolledText(lf,font=F["m"],bg=C["card"],fg=C["text"],
                                                   relief=tk.FLAT,padx=10,pady=6)
        self._auto_log.pack(fill=tk.BOTH,expand=True,pady=(4,0))

    def _mode_changed(self,mode):
        if mode=="hw":
            self._auto_mode_lbl.config(text="需连接设备",fg=C["red"])
        else:
            self._auto_mode_lbl.config(text="仿真模式",fg=C["muted"])

    def _auto_start(self):
        if self.running:
            self._stop_event.set();return
        self._stop_event.clear();self.running=True;algo=self._auto_algo.get()
        try:mr=int(self._auto_rnd.get())
        except:mr=15
        try:tgt=int(self._auto_tgt.get())
        except:tgt=60
        self._auto_log.delete(1.0,tk.END);self._curve.clear();self.q.put(("target",tgt))
        self._auto_log_msg(f"[自动调参] 算法: {algo} | 轮次: {mr} | 目标: {tgt}")
        # 找按钮
        for c in self._pages["auto"].winfo_children():
            if isinstance(c,tk.Frame):
                for cc in c.winfo_children():
                    if isinstance(cc,tk.Frame):
                        for b in cc.winfo_children():
                            if isinstance(b,tk.Button) and ("开始" in (b.cget("text") or "") or "停止" in (b.cget("text") or "")):
                                self._auto_btn=b
        if hasattr(self,'_auto_btn'):
            self._auto_btn.config(text="  停止  ",bg=C["red"],fg="white")
        threading.Thread(target=self._auto_worker,args=(algo,mr,tgt),daemon=True).start()

    def _auto_worker(self,algo,mr,tgt):
        """统一调参引擎: 硬件优先, 未连接则仿真"""
        try:
            self._auto_worker_inner(algo,mr,tgt)
        except Exception as e:
            import traceback
            self._auto_log_msg(f"[致命错误] {e}")
            self._auto_log_msg(traceback.format_exc()[-300:])
            self.q.put(("done",None))

    def _auto_worker_inner(self,algo,mr,tgt):
        from mspm0g_tuner.sim_adapter import SimAdapter
        from mspm0g_tuner.engine import run_tuning_engine
        from mspm0g_tuner.buffer import SpeedBuffer
        import time

        # 判断模式
        want_hw=(self._auto_mode.get()=="hw")
        if want_hw:
            from mspm0g_tuner.bridge import SerialBridge
            port=self._tb_port.get().strip() or "AUTO"
            try: baud=int(self._tb_baud.get())
            except: baud=115200
            bridge=SerialBridge(port=port,baud=baud)
            if not bridge.connect():
                self._auto_log_msg("[错误] 无法打开串口, 检查是否被其他程序占用")
                self.q.put(("done",None));return
            using_hw=True
            self._auto_log_msg("[硬件模式] 串口调参")
            bridge.flush()
            self._auto_log_msg("[检测] 等待数据...")
            samples=bridge.read_samples(5,timeout_s=6.0)
            if len(samples)<2:
                bridge.disconnect()
                self._auto_log_msg("[错误] 未收到 MCU 数据")
                self.q.put(("done",None));return
            self._auto_log_msg(f"[检测] 收到 {len(samples)} 点数据, 开始调参")
        else:
            bridge=SimAdapter(kp=2.0,ki=0.0,target=tgt); using_hw=False
            self._auto_log_msg("[仿真模式] 本地模型")

        # ── 预热: P-only 扫频找起点 ──
        self._auto_log_msg("[预热] P-only 扫频...")
        best_p={"p":3.0,"i":0.0,"d":0.0};best_err=999
        for test_kp in [3.0,6.0,10.0]:
            if self._stop_event.is_set():self._auto_log_msg("[已停止]");self.q.put(("done",None));return
            if using_hw: bridge.set_pid(test_kp,0,0)
            else: bridge.sim.set_pid(test_kp,0,0)
            buf=SpeedBuffer(60)
            for _ in range(60):
                if self._stop_event.is_set():self._auto_log_msg("[已停止]");self.q.put(("done",None));return
                s=bridge.read_sample()
                if s: buf.add(s); self.q.put(("curve",s.get("speed_L",0)))
            m=buf.calculate_metrics()
            cur_v=tgt-m['avg_error']
            self.q.put(("curve",cur_v))
            self._auto_log_msg(f"  预热 P={test_kp:.1f}: speed={cur_v:.0f} tgt={tgt} err={m['avg_error']:.1f} [{m['status']}]")
            if m["avg_error"]<best_err:best_err=m["avg_error"];best_p={"p":test_kp,"i":0.0,"d":0.0}
        # 最佳 P 加初始 I
        best_p["i"]=best_p["p"]*0.3
        self.q.put(("pid",best_p))
        self._auto_log_msg(f"[预热完成] 起点: P={best_p['p']:.1f} I={best_p['i']:.1f}")

        if self._stop_event.is_set():self._auto_log_msg("[已停止]");self.q.put(("done",None));return

        # ── 主调参循环 ──
        if not using_hw:
            bridge=SimAdapter(kp=best_p["p"],ki=best_p["i"],target=tgt)
        else:
            bridge.set_pid(best_p["p"],best_p["i"])
        try:
            final=run_tuning_engine(
                bridge=bridge,config=self.config,current_pid=best_p,
                on_sample=lambda s:self.q.put(("curve",s.get("speed_L",0))),
                on_round_complete=lambda r,pid,m,res:(
                    self.q.put(("pid",pid)),
                    self.q.put(("curve",tgt-m['avg_error'])),
                    self.q.put(("score",f"{max(0,100-m['avg_error']*2-m['overshoot']*0.3):.0f}%")),
                    self.q.put(("rec",f"P={pid['p']:.3f} I={pid['i']:.3f}")),
                    self._auto_log_msg(f"R{r}: speed={tgt-m['avg_error']:.0f} tgt={tgt} err={m['avg_error']:.1f} [{m['status']}] P={pid['p']:.3f} I={pid['i']:.3f}"),
                    (res and res.get("analysis_summary","")) and self._auto_log_msg(f"  LLM: {res.get('analysis_summary','')}")
                ),
                abort_check=lambda:self._stop_event.is_set()
            )
            if using_hw:
                try: bridge.disconnect()
                except: pass
            self._auto_log_msg(f"[完成] 最优: P={final['p']:.3f} I={final['i']:.3f}")
        except Exception as e:
            self._auto_log_msg(f"[异常] {e}")
        finally:
            self.q.put(("done",None))

    def _auto_log_msg(self,msg):self.q.put(("auto_log",msg))

    # ═══ 手动配置页面 ═══
    def _build_manual(self):
        pg=tk.Frame(self._center,bg=C["bg"]);self._pages["manual"]=pg

        bar=_card(pg);bar.pack(fill=tk.X,pady=(0,8))
        r=tk.Frame(bar,bg=C["card"]);r.pack(fill=tk.X)
        for lab,attr,defv in [("Kp","_mp",3.0),("Ki","_mi",1.0),("Kd","_md",0.0)]:
            g=tk.Frame(r,bg=C["card"]);g.pack(side=tk.LEFT,padx=(0,6))
            _lbl(g,lab,F["s"],C["sub"]).pack(anchor=tk.W)
            e=_ent(g,defv,6);setattr(self,attr,e)
        _lbl(r,"目标:",F["s"],C["sub"]).pack(side=tk.LEFT,padx=(8,2))
        self._mtgt=_ent(r,60,4);self._mtgt.pack(side=tk.LEFT,padx=(0,8))
        _lbl(r,"次数:",F["s"],C["sub"]).pack(side=tk.LEFT,padx=(4,2))
        self._mtests=_ent(r,3,3);self._mtests.pack(side=tk.LEFT,padx=(0,8))
        _lbl(r,"秒/次:",F["s"],C["sub"]).pack(side=tk.LEFT,padx=(2,2))
        self._msec=_ent(r,5,3);self._msec.pack(side=tk.LEFT)
        _btn(r,"发送PID",self._m_send,pri=True).pack(side=tk.RIGHT,padx=(4,0))
        _btn(r,"清空曲线",self._m_clear).pack(side=tk.RIGHT,padx=4)
        _btn(r,"模型评估",self._m_model).pack(side=tk.RIGHT,padx=4)
        _btn(r,"开始测试",self._m_start,pri=True).pack(side=tk.RIGHT,padx=4)

        # 日志
        lf=_card(pg);lf.pack(fill=tk.BOTH,expand=True)
        _lbl(lf,"测试日志",F["b"],C["sub"]).pack(anchor=tk.W)
        self._m_log=scrolledtext.ScrolledText(lf,font=F["m"],bg=C["card"],fg=C["text"],
                                                relief=tk.FLAT,padx=10,pady=6)
        self._m_log.pack(fill=tk.BOTH,expand=True,pady=(4,0))

    def _m_clear(self):self._curve.clear();self._score_var.set("--- %");self._rec_var.set("---");self._m_log.delete(1.0,tk.END)

    def _m_send(self):
        if not self._conn:self._m_log_msg("未连接设备");return
        try:p=float(self._mp.get());i=float(self._mi.get());d=float(self._md.get())
        except:self._m_log_msg("PID 数值无效");return
        self._bridge.set_pid(p,i,d)
        try:t=int(self._mtgt.get());self._bridge.set_target(t,t)
        except:pass
        self._m_log_msg(f"已发送: P={p:.3f} I={i:.3f} D={d:.3f}")
        self.pid={"p":p,"i":i,"d":d}

    def _m_start(self):
        if self.running:self._stop_event.set();return  # 停止
        self._stop_event.clear();self.running=True
        try:p=float(self._mp.get());i=float(self._mi.get());d=float(self._md.get())
        except:p=3.0;i=1.0;d=0.0
        try:tests=int(self._mtests.get());sec=int(self._msec.get());tgt=int(self._mtgt.get())
        except:tests=3;sec=5;tgt=60
        self._curve.clear();self._m_log.delete(1.0,tk.END)
        self._m_log_msg(f"开始测试: P={p:.3f} I={i:.3f} D={d:.3f}")
        threading.Thread(target=self._m_run,args=(p,i,d,tests,sec,tgt),daemon=True).start()

    def _m_run(self,p,i,d,tests,sec,tgt):
        from mspm0g_tuner.car_model import CarSimulator
        from mspm0g_tuner.buffer import SpeedBuffer
        all_m=[]
        for ti in range(tests):
            if self._stop_event.is_set():self._m_log_msg("[已停止]");break
            sim=CarSimulator();sim.target=tgt;sim.set_pid(p,i,d)
            buf=SpeedBuffer(200)
            for _ in range(int(sec*50)):
                s=sim.step();buf.add(s)
                self.q.put(("m_curve",s.get("speed_L",0)))
                time.sleep(0.008)
            m=buf.calculate_metrics();all_m.append(m)
            self._m_log_msg(f"  第{ti+1}次: 误差={m['avg_error']:.1f} 超调={m['overshoot']:.1f}% [{m['status']}]")
        avg_err=sum(x["avg_error"] for x in all_m)/len(all_m)
        avg_over=sum(x["overshoot"] for x in all_m)/len(all_m)
        score=max(0,100-avg_err*3-avg_over*0.5)
        self.q.put(("score",f"{score:.1f} %"))
        rec_p=p*(0.7+0.3*score/100);rec_i=i*(0.5+0.5*score/100) if score<70 else i
        self.q.put(("rec",f"P={rec_p:.3f}  I={rec_i:.3f}"))
        self._m_log_msg(f"稳定性: {score:.1f}% | 推荐: P={rec_p:.3f} I={rec_i:.3f}")
        self.running=False

    def _m_model(self):
        try:p=float(self._mp.get());i=float(self._mi.get());d=float(self._md.get())
        except:p=3.0;i=1.0;d=0.0
        try:tgt=int(self._mtgt.get())
        except:tgt=60
        from mspm0g_tuner.car_model import CarSimulator
        from mspm0g_tuner.buffer import SpeedBuffer
        from mspm0g_tuner.llm.client import LLMTuner
        sim=CarSimulator();sim.target=tgt;sim.set_pid(p,i,d)
        buf=SpeedBuffer(200)
        for _ in range(250):
            s=sim.step();buf.add(s)
            self.q.put(("m_curve",s.get("speed_L",0)))
        m=buf.calculate_metrics()
        tuner=LLMTuner(self.config)
        self._m_log_msg("请求 LLM 评估...")
        res=tuner.analyze(buf.to_prompt_data(),"")
        if res.get("p",-1)>0:
            rec=f"P={res['p']:.3f}  I={res['i']:.3f}"
            msg=f"LLM 分析: {res.get('analysis_summary','')}\n\n推荐 PID: {rec}"
        else:
            rec=f"P={p*0.9:.3f}  I={i*1.1:.3f}"
            msg=f"LLM 不可用 (检查 API Key)\n\n规则推荐: {rec}"
        self._m_log_msg(f"评估完成: 误差={m['avg_error']:.1f} [{m['status']}]")
        self._rec_var.set(rec);self.q.put(("rec",rec))
        score=max(0,100-m["avg_error"]*3-m["overshoot"]*0.5)
        self.q.put(("score",f"{score:.1f} %"))
        messagebox.showinfo("模型评估结果",msg+f"\n\n当前: P={p:.3f} I={i:.3f} D={d:.3f}\n误差={m['avg_error']:.1f} 超调={m['overshoot']:.1f}%")

    def _m_log_msg(self,msg):self.q.put(("m_log",msg))

    # ═══ LLM 设置页面 ═══
    def _build_settings(self):
        pg=tk.Frame(self._center,bg=C["bg"]);self._pages["settings"]=pg
        c=_card(pg);c.pack(fill=tk.BOTH,expand=True)
        _lbl(c,"LLM 配置",F["h"]).pack(anchor=tk.W,pady=(0,10))

        # 快捷模板
        r0=tk.Frame(c,bg=C["card"]);r0.pack(fill=tk.X,pady=(0,8))
        _lbl(r0,"快捷模板:",F["b"],C["sub"]).pack(side=tk.LEFT,padx=(0,6))

        self.PRESETS={
            "DeepSeek":  {"url":"https://api.deepseek.com/v1","model":"deepseek-v4-pro[1m]","provider":"openai",
                          "models":["deepseek-v4-pro[1m]","deepseek-v4-pro","deepseek-chat","deepseek-reasoner"]},
            "ChatGPT":   {"url":"https://api.openai.com/v1","model":"gpt-5.1","provider":"openai",
                          "models":["gpt-5.1","gpt-5","gpt-4.1","o4-mini"]},
            "MiniMax":   {"url":"https://api.minimax.chat/v1","model":"MiniMax-M2.5","provider":"openai",
                          "models":["MiniMax-M2.5","MiniMax-Text-01","abab7-chat"]},
            "Claude":    {"url":"https://api.anthropic.com","model":"claude-opus-4-8","provider":"anthropic",
                          "models":["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5"]},
            "豆包":      {"url":"https://ark.cn-beijing.volces.com/api/v3","model":"doubao-pro-256k","provider":"openai",
                          "models":["doubao-pro-256k","doubao-pro-128k","doubao-lite-32k"]},
        }
        self._preset_var=tk.StringVar()
        cb=ttk.Combobox(r0,textvariable=self._preset_var,values=list(self.PRESETS.keys()),state="readonly",width=10,font=F["b"])
        cb.pack(side=tk.LEFT,padx=(0,6))
        cb.bind("<<ComboboxSelected>>",lambda e:self._apply_preset())
        _btn(r0,"应用",lambda:self._apply_preset()).pack(side=tk.LEFT)

        self._sv={}
        # API Key (text)
        rw=tk.Frame(c,bg=C["card"]);rw.pack(fill=tk.X,pady=3)
        _lbl(rw,"API Key",F["b"],C["sub"],width=12,anchor=tk.W).pack(side=tk.LEFT)
        v=tk.StringVar(value=str(self.config.get("LLM_API_KEY","")))
        tk.Entry(rw,textvariable=v,show="*",font=F["m"],fg=C["text"],bg=C["bg"],
                 relief=tk.FLAT,width=42,insertbackground=C["accent"],
                 highlightbackground=C["border"],highlightthickness=1).pack(side=tk.LEFT,ipady=4)
        self._sv["LLM_API_KEY"]=v

        # Base URL (text)
        rw=tk.Frame(c,bg=C["card"]);rw.pack(fill=tk.X,pady=3)
        _lbl(rw,"Base URL",F["b"],C["sub"],width=12,anchor=tk.W).pack(side=tk.LEFT)
        v=tk.StringVar(value=str(self.config.get("LLM_API_BASE_URL","")))
        tk.Entry(rw,textvariable=v,font=F["m"],fg=C["text"],bg=C["bg"],
                 relief=tk.FLAT,width=42,insertbackground=C["accent"],
                 highlightbackground=C["border"],highlightthickness=1).pack(side=tk.LEFT,ipady=4)
        self._sv["LLM_API_BASE_URL"]=v

        # Provider (dropdown)
        rw=tk.Frame(c,bg=C["card"]);rw.pack(fill=tk.X,pady=3)
        _lbl(rw,"服务商",F["b"],C["sub"],width=12,anchor=tk.W).pack(side=tk.LEFT)
        self._prov_var=tk.StringVar(value=str(self.config.get("LLM_PROVIDER","openai")))
        pc=ttk.Combobox(rw,textvariable=self._prov_var,values=["openai","anthropic"],state="readonly",width=14,font=F["m"])
        pc.pack(side=tk.LEFT)
        self._sv["LLM_PROVIDER"]=self._prov_var

        # Model (dropdown)
        rw=tk.Frame(c,bg=C["card"]);rw.pack(fill=tk.X,pady=3)
        _lbl(rw,"模型名称",F["b"],C["sub"],width=12,anchor=tk.W).pack(side=tk.LEFT)
        self._model_var=tk.StringVar(value=str(self.config.get("LLM_MODEL_NAME","gpt-4o")))
        all_models=sorted(set(m for p in self.PRESETS.values() for m in p["models"]))
        mc=ttk.Combobox(rw,textvariable=self._model_var,values=all_models,width=24,font=F["m"])
        mc.pack(side=tk.LEFT)
        mc.bind("<FocusIn>",lambda e:mc.config(values=sorted(set(m for p in self.PRESETS.values() for m in p["models"]))))
        self._sv["LLM_MODEL_NAME"]=self._model_var

        _btn(c,"保存配置",self._save_cfg,pri=True).pack(pady=(16,0))

    def _apply_preset(self,presets=None):
        name=self._preset_var.get()
        if name not in self.PRESETS:return
        p=self.PRESETS[name]
        self._sv["LLM_API_BASE_URL"].set(p["url"])
        self._model_var.set(p["model"])
        self._prov_var.set(p["provider"])
        # update model dropdown with this provider's models
        for w in self._pages["settings"].winfo_children():
            if isinstance(w,tk.Frame):
                for c in w.winfo_children():
                    if isinstance(c,tk.Frame):
                        for r in c.winfo_children():
                            if isinstance(r,tk.Frame):
                                for x in r.winfo_children():
                                    if isinstance(x,ttk.Combobox):
                                        cur=x.cget("values")
                                        if cur and any("gpt" in str(v) or "deepseek" in str(v) or "claude" in str(v) or "MiniMax" in str(v) or "doubao" in str(v) for v in cur):
                                            x.config(values=p.get("models",list(cur)))

    def _save_cfg(self):
        cfg={k:v.get() for k,v in self._sv.items()}
        for k in DEFAULT_CONFIG:
            if k not in cfg:cfg[k]=DEFAULT_CONFIG[k]
        try:
            with open("config.json","w",encoding="utf-8") as f:json.dump(cfg,f,indent=2,ensure_ascii=False)
            self.config=cfg;messagebox.showinfo("","配置已保存")
        except Exception as e:messagebox.showerror("",str(e))

    # ═══ 消息轮询 ═══
    def _poll(self):
        for _ in range(30):
            try:msg=self.q.get_nowait()
            except queue.Empty:break
            tp,data=msg
            if tp=="pid":
                for k in ("p","i","d"):
                    if k in data and k in self._av:self._av[k].set(f"{data[k]:.3f}")
            elif tp in ("curve","m_curve"):
                self._curve.max_y=max(self._curve.target*2,120)
                # 限频: 最多保留最近200点, 每2个点刷一次画布
                self._curve.data.append(data)
                if len(self._curve.data)>self._curve.max_pts:self._curve.data.pop(0)
                if len(self._curve.data)%2==0:
                    self._curve.draw()
            elif tp=="target":self._curve.target=data
            elif tp=="auto_log":
                self._auto_log.insert(tk.END,str(data)+"\n")
                self.root.after_idle(lambda:self._auto_log.see(tk.END))
            elif tp=="m_log":
                self._m_log.insert(tk.END,str(data)+"\n")
                self.root.after_idle(lambda:self._m_log.see(tk.END))
            elif tp=="score":self._score_var.set(str(data))
            elif tp=="rec":self._rec_var.set(str(data))
            elif tp=="done":
                self.running=False;self._stop_event.clear()
                if hasattr(self,'_auto_btn'):
                    self._auto_btn.config(text="开始自动调参",state=tk.NORMAL,bg=C["accent"],fg="white")
        self.root.after(30,self._poll)

def main():
    root=tk.Tk()
    try:root.iconbitmap(default="")
    except:pass
    App(root);root.mainloop()

if __name__=="__main__":main()
