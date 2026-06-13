import streamlit as st
import os
import time
import pandas as pd
from dotenv import load_dotenv
load_dotenv()
from services.auth.login_wall import render_login_wall
from services.state.session_defaults import initial_session_defaults
from services.config.workout_config import EXERCISE_OPTIONS, EXERCISE_ICONS
from services.ui.style_loader import load_css, inject_local_font, inject_webrtc_styles
from services.persistence.exercise_repository import init_db
from streamlit_webrtc import webrtc_streamer, WebRtcMode
from services.vision.exercise_video_processor import VideoProcessorClass
from services.tracking.metrics import sync_metrics_update
from services.persistence.exercise_repository import get_users_exercises
from groq import Groq
from services.coaching.llm import LLMCoach
from services.coaching.tts import TextToSpeech
from services.coaching.voice_pipeline import VoicePipeline, autoplay_audio

  
def main():
    st.set_page_config(
        page_icon="🏋️‍♀️",
        page_title="AI Real-time GYM Coach",
        initial_sidebar_state="expanded",
        layout="centered"
    )

    load_css(os.path.join(os.getcwd(), "static", "style.css"))
    inject_local_font(os.path.join(os.getcwd(), "static", "AdobeClean.otf"), "AdobeClean")

    init_db()

    if not render_login_wall():
        return 

    initial_session_defaults()

    if "voice_pipeline" not in st.session_state:
        try:
            api_key = os.environ.get("GROQ_API_KEY", "")

            if not api_key and hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
                api_key = st.secrets["GROQ_API_KEY"]

            if not api_key:
                st.error("❌ GROQ_API_KEY not found. Check your .env file.")
                st.session_state.voice_pipeline = None
            else:
                groq_client = Groq(api_key=api_key)
                llm_coach = LLMCoach(groq_client)
                tts = TextToSpeech()
                st.session_state.voice_pipeline = VoicePipeline(llm_coach, tts)

                if not st.session_state.get("welcomed"):
                    username = st.session_state.get("username", "")
                    result = st.session_state.voice_pipeline.process_event(
                        event="login",
                        exercise="",
                        metrics={"issue": f"The user's name is {username}. Greet them warmly and hype them up for their workout."}
                    )
                    if result:
                        st.session_state.audio_to_play, st.session_state.coach_feedback = result
                    st.session_state.welcomed = True

        except Exception as e:
            st.session_state.voice_pipeline = None
            st.error(f"❌ Voice pipeline failed to start: {e}")

    workout_started = st.session_state.get("workout_started", False)
    
    with st.sidebar:
        st.title("🏋️‍♂️ Apna AI Coach")

        if st.session_state.username:
            st.caption(f"👤 Login as {st.session_state.username}")

        st.divider()

        st.subheader("Workout Plan")

        if not workout_started:
            plan_exercise = st.selectbox("Exercise", options=EXERCISE_OPTIONS, key="plan_exercise")

            plan_sets = st.number_input("Sets", min_value=0, max_value=50, key="plan_sets", step=1)

            plan_reps = st.number_input("Reps per Set", min_value=0, max_value=50, key="plan_reps", step=1)

            st.markdown("")

            start_session_button = st.button("Start Workout", width="stretch", key="start_session_button")

            if start_session_button:
                st.session_state.exercise_type = plan_exercise
                st.session_state.target_sets = int(plan_sets)
                st.session_state.reps_per_set = int(plan_reps)
                st.session_state.reps = 0
                st.session_state.workout_started = True
                st.session_state.set_cycle_started_at = time.time()
                st.session_state.last_saved_sets_completed = 0

                if st.session_state.voice_pipeline:
                    result = st.session_state.voice_pipeline.process_event(
                        event="workout_started",
                        exercise=plan_exercise,
                        metrics={}
                    )
                    
                    if result:
                        st.session_state.audio_to_play, st.session_state.coach_feedback = result

                st.session_state.last_notified_sets_completed = 0
                st.session_state.last_notified_workout_complete = False
                st.rerun()
        else:
            exercise = st.session_state.get("exercise_type")
            sets = st.session_state.get("target_sets")
            reps = st.session_state.get("reps_per_set")

            st.info(f"**{exercise}** -- {sets} Sets / {reps} Reps")

            end_session_button = st.button("End Workout", key="end_session_button", width="stretch")

            if end_session_button:
                st.session_state.workout_started = False

                # store summary before clearing
                st.session_state.workout_summary = {
                    "exercise": exercise,
                    "total_reps": st.session_state.get("reps", 0),
                    "sets_completed": st.session_state.get("sets_completed", 0),
                    "target_sets": st.session_state.get("target_sets", 0),
                    "reps_per_set": st.session_state.get("reps_per_set", 0),
                    "form_score": st.session_state.get("form_score", 100),
                }
                
                if st.session_state.voice_pipeline:
                    result = st.session_state.voice_pipeline.process_event(
                        event="workout_completed",
                        exercise=exercise,
                        metrics={}
                    )
                    if result:
                        st.session_state.audio_to_play, st.session_state.coach_feedback = result

                st.rerun()

        if workout_started:
            st.divider()

            exercise = st.session_state.get("exercise_type")
            total_reps = st.session_state.get("reps")
            current_set_reps = st.session_state.get("current_set_reps")
            reps_per_set = st.session_state.get("reps_per_set")
            sets_completed = st.session_state.get("sets_completed")
            target_sets = st.session_state.get("target_sets")
            form_score = st.session_state.get("form_score", 100)

            st.subheader("Progress")

            # Rep progress ring
            ring_pct = (current_set_reps / reps_per_set) if reps_per_set > 0 else 0
            ring_pct = min(ring_pct, 1.0)
            circumference = 2 * 3.14159 * 54
            dash = ring_pct * circumference
            gap = circumference - dash
            if form_score >= 80:
                ring_color = "#00E5FF"
            elif form_score >= 50:
                ring_color = "#FFB347"
            else:
                ring_color = "#FF4C4C"

            st.markdown(f"""
            <div style="display:flex;flex-direction:column;align-items:center;margin:8px 0 16px 0">
                <svg width="140" height="140" viewBox="0 0 120 120">
                    <circle cx="60" cy="60" r="54" fill="none" stroke="#1E2433" stroke-width="10"/>
                    <circle cx="60" cy="60" r="54" fill="none" stroke="{ring_color}" stroke-width="10"
                        stroke-dasharray="{dash:.1f} {gap:.1f}"
                        stroke-dashoffset="{circumference * 0.25:.1f}"
                        stroke-linecap="butt"
                        style="transition:stroke-dasharray 0.3s ease,stroke 0.4s ease;"/>
                    <text x="60" y="52" text-anchor="middle" fill="#fff" font-size="22" font-weight="600" font-family="AdobeClean,sans-serif">{current_set_reps}</text>
                    <text x="60" y="70" text-anchor="middle" fill="#888" font-size="11" font-family="AdobeClean,sans-serif">of {reps_per_set} reps</text>
                    <text x="60" y="86" text-anchor="middle" fill="{ring_color}" font-size="10" font-family="AdobeClean,sans-serif">SET {sets_completed + 1} / {target_sets}</text>
                </svg>
                <div style="margin-top:4px;font-size:13px;color:#888;">Total Reps: <span style="color:#fff;font-weight:600">{total_reps}</span></div>
            </div>
            """, unsafe_allow_html=True)

            # Form score badge
            if form_score >= 80:
                badge_color = "#00E5FF"
                badge_label = "GREAT FORM"
            elif form_score >= 50:
                badge_color = "#FFB347"
                badge_label = "NEEDS WORK"
            else:
                badge_color = "#FF4C4C"
                badge_label = "POOR FORM"

            st.markdown(f"""
            <div style="display:flex;align-items:center;justify-content:space-between;background:#181D2A;border:1px solid rgba(255,255,255,0.08);padding:10px 16px;margin-bottom:12px;">
                <span style="font-size:13px;color:#888;">Form Score</span>
                <span style="font-size:18px;font-weight:700;color:{badge_color};">{form_score}% <span style="font-size:11px;opacity:0.7">{badge_label}</span></span>
            </div>
            """, unsafe_allow_html=True)

            st.divider()

            if exercise == "Squats":
                st.subheader("Squat Metrics")
                st.metric("Knee Angle", f"{st.session_state.knee_angle}°")
                st.metric("Back Angle", f"{st.session_state.back_angle}°")
                st.metric("Depth Status", st.session_state.depth_status)

            elif exercise == "Push-ups":
                st.subheader("Push-up Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Body Alignment", st.session_state.body_alignment)
                st.metric("Hip Position", st.session_state.hip_status)

            elif exercise == "Biceps Curls (Dumbbell)":
                st.subheader("Curl Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Shoulder Stability", st.session_state.shoulder_status)
                st.metric("Swing Detection", st.session_state.swing_status)

            elif exercise == "Shoulder Press":
                st.subheader("Shoulder Press Metrics")
                st.metric("Elbow Angle", f"{st.session_state.elbow_angle}°")
                st.metric("Arm Extension", st.session_state.extension_status)
                st.metric("Back Arch", st.session_state.back_arch_status)

            elif exercise == "Lunges":
                st.subheader("Lunge Metrics")
                st.metric("Front Knee Angle", f"{st.session_state.front_knee_angle}°")
                st.metric("Torso Angle", f"{st.session_state.torso_angle}°")
                st.metric("Balance Status", st.session_state.balance_status)

    st.title("AI Real-time GYM Coach")
    st.markdown("#### Real-time pose detection with proactive AI voice coaching")

    # Workout summary card
    summary = st.session_state.get("workout_summary")
    if summary and not workout_started:
        ex = summary["exercise"]
        icon = EXERCISE_ICONS.get(ex, "🏋️")
        score = summary["form_score"]
        score_color = "#00E5FF" if score >= 80 else ("#FFB347" if score >= 50 else "#FF4C4C")
        st.markdown(f"""
        <div style="background:#181D2A;border:1px solid rgba(0,229,255,0.25);padding:24px 28px;margin:16px 0;">
            <div style="font-size:13px;color:#888;margin-bottom:8px;letter-spacing:0.1em;">SESSION COMPLETE</div>
            <div style="font-size:22px;font-weight:700;margin-bottom:16px;">{icon} {ex}</div>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px;">
                <div style="background:#0A0D14;padding:12px;text-align:center;">
                    <div style="font-size:26px;font-weight:700;color:#00E5FF;">{summary["total_reps"]}</div>
                    <div style="font-size:11px;color:#888;margin-top:2px;">TOTAL REPS</div>
                </div>
                <div style="background:#0A0D14;padding:12px;text-align:center;">
                    <div style="font-size:26px;font-weight:700;color:#00E5FF;">{summary["sets_completed"]}/{summary["target_sets"]}</div>
                    <div style="font-size:11px;color:#888;margin-top:2px;">SETS DONE</div>
                </div>
                <div style="background:#0A0D14;padding:12px;text-align:center;">
                    <div style="font-size:26px;font-weight:700;color:{score_color};">{score}%</div>
                    <div style="font-size:11px;color:#888;margin-top:2px;">FORM SCORE</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

 
    if st.session_state.get("audio_to_play"):
        autoplay_audio(st.session_state.audio_to_play)
        st.session_state.audio_to_play = None
        st.session_state.coach_feedback = st.session_state.get("coach_feedback")

    if st.session_state.get("coach_feedback"):
        st.markdown("")
        st.success(f"🤖 **Coach:** {st.session_state.coach_feedback}")

    if not workout_started:
        st.markdown(
            """
            <div style="
                border: 10px dashed #444;
                border-radius: 0px;
                padding: 48px 32px;
                text-align: center;
                color: #888;
                margin-top: 32px;
                margin-bottom: 32px;
            ">
                <h2 style="color:#ccc; margin-bottom:8px;">👈 Set your workout plan</h2>
                <p style="font-size:1.05rem;">
                    Choose your exercise, sets and reps in the sidebar,<br>
                    then click <strong>Start Workout</strong> to activate the camera and AI coach.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        context = webrtc_streamer(
            key="exercise-analysis",
            mode=WebRtcMode.SENDRECV,
            video_processor_factory=VideoProcessorClass,
            rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
            media_stream_constraints={
                "video": True,
                "audio": False
            },
            async_processing=True
        )

        sync_metrics_update(context)

        if context.state.playing:
            time.sleep(0.25)
            st.rerun()

        inject_webrtc_styles()

    st.divider()

    st.markdown("#### Workout History")

    user_id = st.session_state.get("user_id", 0)

    if isinstance(user_id, int):
        history_rows = get_users_exercises(user_id)

        arr = [
            {
                "Exercise": row['exercise_name'],
                "Reps": row['reps'],
                "Sets": row['sets'],
                "Time (sec)": row['time'],
                "Date": row['created_at']
            }
            for row in history_rows
        ]

        df = pd.DataFrame(arr)

        if not df.empty:
            df["Date"] = pd.to_datetime(df["Date"]).dt.date
            agg_df = df.groupby(["Exercise", "Date"]).agg({
                "Reps": 'sum',
                "Sets": "sum",
                "Time (sec)": "sum"
            }).reset_index()

            # Bar chart — reps per exercise per day
            chart_df = agg_df.pivot_table(index="Date", columns="Exercise", values="Reps", aggfunc="sum").fillna(0)
            st.bar_chart(chart_df, height=220)

            agg_df.index += 1
            with st.expander("View full history table"):
                st.table(agg_df)
        else:
            st.info("No workout history found.")


if __name__ == "__main__":
    main()
    