import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import uuid

# --- 1. 数据库配置与初始化 ---
DB_FILE = "housing_filing.db"

def init_db():
    """初始化数据库表结构"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id TEXT PRIMARY KEY,
            business_no TEXT,
            apply_time TEXT,
            status TEXT,
            
            -- 楼栋信息
            bld_name TEXT, bld_address TEXT, total_floors INTEGER, total_units INTEGER,
            
            -- 房屋信息
            house_no TEXT, house_type TEXT, house_area REAL, rights_status TEXT, presale_permit TEXT,
            
            -- 卖方信息
            seller_name TEXT, seller_code TEXT, seller_rep TEXT, seller_contact TEXT,
            
            -- 买方信息
            buyer_name TEXT, buyer_id TEXT, buyer_contact TEXT, buyer_share_type TEXT,
            
            -- 审核信息
            audit_comment TEXT, audit_time TEXT
        )
    ''')
    conn.commit()
    conn.close()

# 启动时初始化
init_db()

# --- 2. 核心业务逻辑函数 ---

def generate_business_no():
    """生成唯一业务编号: 20231027-A1B2"""
    return f"{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"

def save_application(data):
    """保存申请数据"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO applications VALUES (
            :id, :business_no, :apply_time, :status,
            :bld_name, :bld_address, :total_floors, :total_units,
            :house_no, :house_type, :house_area, :rights_status, :presale_permit,
            :seller_name, :seller_code, :seller_rep, :seller_contact,
            :buyer_name, :buyer_id, :buyer_contact, :buyer_share_type,
            :audit_comment, :audit_time
        )
    ''', data)
    conn.commit()
    conn.close()

def update_audit_status(app_id, status, comment):
    """更新审核状态"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    time_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("UPDATE applications SET status = ?, audit_comment = ?, audit_time = ? WHERE id = ?", 
              (status, comment, time_now, app_id))
    conn.commit()
    conn.close()

def get_data(status_filter=None):
    """获取数据列表"""
    conn = sqlite3.connect(DB_FILE)
    query = "SELECT * FROM applications"
    if status_filter:
        query += f" WHERE status = '{status_filter}'"
    query += " ORDER BY apply_time DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# --- 3. 页面 UI 构建 ---
st.set_page_config(page_title="商品现房备案系统", page_icon="🏠", layout="wide")

# 侧边栏：角色与导航
with st.sidebar:
    st.title("🏠 商品现房备案")
    st.markdown("---")
    role = st.selectbox("当前登录身份", ["👨‍💼 申请人 (开发商/代理)", "👮 审核员 (房管局)"])
    
    if role.startswith("👨‍💼"):
        menu = st.radio("业务菜单", ["📝 创建业务", "🗂️ 我的业务列表"])
    else:
        menu = st.radio("管理菜单", ["🔍 待审核列表", "📊 所有业务档案"])

# === 模块：创建业务 (申请人) ===
if role.startswith("👨‍💼") and menu == "📝 创建业务":
    st.header("📝 新建商品现房备案申请")
    st.markdown("请录入完整信息，系统将自动生成业务编号。")
    
    with st.form("apply_form"):
        # 分组：楼栋与房屋
        st.subheader("1. 楼栋与房屋信息")
        c1, c2, c3 = st.columns(3)
        bld_name = c1.text_input("楼栋名称/编号 *")
        bld_address = c2.text_input("项目地址 *")
        presale_permit = c3.text_input("预售/现售证号 *")
        
        c4, c5, c6 = st.columns(3)
        house_no = c4.text_input("房号 *")
        house_area = c5.number_input("建筑面积 (㎡) *", min_value=0.0)
        rights_status = c6.selectbox("当前产权状况", ["现房", "在建工程抵押", "查封"])
        
        # 折叠更多非必填项
        with st.expander("更多楼栋细节 (选填)"):
            ec1, ec2 = st.columns(2)
            total_floors = ec1.number_input("总层数", value=1)
            total_units = ec2.number_input("总单元数", value=1)
            house_type = st.selectbox("户型", ["住宅-平层", "住宅-复式", "商业", "办公", "其他"])

        st.markdown("---")
        
        # 分组：买卖双方
        st.subheader("2. 买卖双方信息")
        col_seller, col_buyer = st.columns(2)
        
        with col_seller:
            st.info("卖方 (开发商)")
            seller_name = st.text_input("开发商名称 *")
            seller_code = st.text_input("统一社会信用代码 *")
            seller_rep = st.text_input("法定代表人")
            seller_contact = st.text_input("卖方联系电话 *")
            
        with col_buyer:
            st.warning("买方 (购房人)")
            buyer_name = st.text_input("买方姓名/单位 *")
            buyer_id = st.text_input("身份证/证件号 *")
            buyer_contact = st.text_input("买方联系电话 *")
            buyer_share_type = st.selectbox("共有情况", ["单独所有", "共同共有", "按份共有"])

        st.markdown("---")
        submitted = st.form_submit_button("🚀 提交备案申请", type="primary")
        
        if submitted:
            # 数据完整性校验
            required_fields = [bld_name, bld_address, presale_permit, house_no, seller_name, seller_code, buyer_name, buyer_id]
            if any(f == "" for f in required_fields) or house_area <= 0:
                st.error("❌ 提交失败：请检查所有带 * 的必填项，且面积必须大于0。")
            else:
                # 生成数据并保存
                biz_no = generate_business_no()
                new_data = {
                    "id": str(uuid.uuid4()),
                    "business_no": biz_no,
                    "apply_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "待审核",
                    "bld_name": bld_name, "bld_address": bld_address, "total_floors": total_floors, "total_units": total_units,
                    "house_no": house_no, "house_type": house_type, "house_area": house_area, "rights_status": rights_status, "presale_permit": presale_permit,
                    "seller_name": seller_name, "seller_code": seller_code, "seller_rep": seller_rep, "seller_contact": seller_contact,
                    "buyer_name": buyer_name, "buyer_id": buyer_id, "buyer_contact": buyer_contact, "buyer_share_type": buyer_share_type,
                    "audit_comment": "", "audit_time": ""
                }
                save_application(new_data)
                st.success(f"✅ 提交成功！业务编号：{biz_no}，请在列表查看进度。")

# === 模块：业务列表 (申请人) ===
elif role.startswith("👨‍💼") and menu == "🗂️ 我的业务列表":
    st.header("🗂️ 业务办理进度")
    df = get_data() # 实际场景通常会根据当前用户过滤，这里显示全部以便演示
    if df.empty:
        st.info("暂无记录")
    else:
        # 使用更美观的数据展示组件
        for i, row in df.iterrows():
            status_color = "red" if "驳回" in row['status'] else "green" if "通过" in row['status'] else "orange"
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([2, 2, 3, 2])
                c1.markdown(f"**{row['business_no']}**")
                c2.caption(row['apply_time'])
                c3.text(f"{row['bld_name']} - {row['house_no']}")
                c4.markdown(f":{status_color}[{row['status']}]")
                if row['audit_comment']:
                    st.caption(f"审核意见: {row['audit_comment']}")

# === 模块：待审核 (审核员) ===
elif role.startswith("👮") and menu == "🔍 待审核列表":
    st.header("🔍 待审核业务")
    df = get_data("待审核")
    
    if df.empty:
        st.success("🎉 目前没有待处理的任务")
    else:
        for i, row in df.iterrows():
            with st.expander(f"待审: {row['business_no']} | {row['bld_name']} {row['house_no']} ({row['buyer_name']})", expanded=True):
                # 展示详情
                t1, t2 = st.tabs(["🏠 房屋详情", "👥 人员信息"])
                with t1:
                    st.write(f"**地址**: {row['bld_address']}")
                    st.write(f"**面积**: {row['house_area']}㎡ | **用途**: {row['house_type']}")
                    st.write(f"**预售证**: {row['presale_permit']} | **状态**: {row['rights_status']}")
                with t2:
                    st.write(f"**卖方**: {row['seller_name']} (信用代码: {row['seller_code']})")
                    st.write(f"**买方**: {row['buyer_name']} (证件: {row['buyer_id']})")
                
                # 审核操作区
                st.markdown("---")
                with st.form(key=f"audit_form_{row['id']}"):
                    comment = st.text_area("审核意见 (驳回必填)", placeholder="请输入审核说明...")
                    c_pass, c_reject = st.columns(2)
                    
                    pass_btn = c_pass.form_submit_button("✅ 通过备案")
                    reject_btn = c_reject.form_submit_button("🚫 驳回申请")
                    
                    if pass_btn:
                        update_audit_status(row['id'], "审核通过", comment or "符合规定，予以通过")
                        st.rerun()
                    if reject_btn:
                        if not comment:
                            st.error("⚠️ 驳回操作必须填写审核意见！")
                        else:
                            update_audit_status(row['id'], "审核驳回", comment)
                            st.rerun()

# === 模块：所有业务档案 (审核员) ===
elif role.startswith("👮") and menu == "📊 所有业务档案":
    st.header("📊 业务档案数据库")
    df = get_data()
    st.dataframe(df, use_container_width=True, height=500)