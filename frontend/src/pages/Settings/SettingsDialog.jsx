import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { X } from 'lucide-react';
import Settings from './Settings';
import './SettingsDialog.css';

export default function SettingsDialog() {
  const dialogRef = useRef(null);
  const navigate = useNavigate();
  useEffect(() => {
    const dialog = dialogRef.current;
    const previousFocus = document.activeElement;
    dialog.showModal();
    return () => {
      dialog.close();
      previousFocus?.focus();
    };
  }, []);
  const close = () => navigate('/');
  return (
    <dialog ref={dialogRef} className="settings-dialog" aria-label="Settings" onCancel={(event) => { event.preventDefault(); close(); }} onClick={(event) => { if (event.target === event.currentTarget) close(); }}>
      <div className="settings-dialog-inner">
        <button className="settings-dialog-close" onClick={close} aria-label="Close settings"><X size={20} /></button>
        <Settings />
      </div>
    </dialog>
  );
}
