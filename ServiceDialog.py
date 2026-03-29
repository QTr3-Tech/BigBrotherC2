 import customtkinter

class ServiceDialog(customtkinter.CTkToplevel):
    def __init__(self, master, **kwargs):
        super().__init__(**kwargs)

        self.master = master
        self.title("Create Task Schedual Dialog")
        self.lift()
        self.attributes("-topmost", True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.geometry("500x350")
        self.grab_set()
        self.dialog_data = ""
        self.resizable(False, False)
        self.RunAsAdminVar = customtkinter.BooleanVar(value=True)
        self.persist_client = customtkinter.BooleanVar(value=True)
        self._create_gui()
        # RUNNING AS ADMIN (WO SPECI FY THE DOMAIN)
        #/ru SYSTEM
        # SETTING THE HIGHEST PRIVILAGES
        # /rl HIGHEST
        # /tn task-name
        # /tr task_run (program to run)

    def _create_gui(self):
        self.task_name_entry = customtkinter.CTkEntry(self, placeholder_text="Enter Task Name Here (The Name in task schedule)")
        self.task_run_entry = customtkinter.CTkEntry(self, placeholder_text="Path to executable")
        #self.user_combobox = customtkinter.CTkComboBox(self, values=self.users_list)
        self.label = customtkinter.CTkLabel(self, text="Task Scheduler Dialog.", font=("Helvitica", 16))
        self.sbmt_btn = customtkinter.CTkButton(self, text="Submit", font=("", 14), command=self._ok)
        self.client_checkbox = customtkinter.CTkCheckBox(self, text="Persist Client", variable=self.persist_client)
        self.admin_checkbox = customtkinter.CTkCheckBox(self, text="Run Target Schedual as Administrator (Default)", variable=self.RunAsAdminVar)

        self.task_name_entry.place(x=80, y=125)
        self.task_run_entry.place(x=270, y=125)
        #self.user_combobox.place(x=150, y=175)
        self.label.place(x=150, y=40)
        self.client_checkbox.place(x=100, y=180)
        self.admin_checkbox.place(x=100, y=220)
        self.sbmt_btn.place(x=150, y=270)
        self.bind("<Return>", lambda x: self._ok())
        
    def _on_close(self):
            self.grab_release()
            self.destroy()

    def get_value(self):
            self.master.wait_window(self)
            if not self.dialog_data == "":
                return self.dialog_data
            else: pass

    def _ok(self):
        if self.persist_client.get() == True:
             self.dialog_data = f"{self.task_name_entry.get()}|exec|SYSTEM"
        else:
             self.dialog_data = f"{self.task_name_entry.get()}|{self.task_run_entry.get()}|SYSTEM"
        self.grab_release()
        self.destroy()
        
if __name__ == "__main__":
    root = customtkinter.CTk()
    root.geometry("1000x500")
    customtkinter.CTkButton(root, command=lambda: print(ServiceDialog(root).get_value())).pack()
    root.mainloop()