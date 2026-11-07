"use client";
import * as React from "react";
import { NavMain } from "@/components/dashboardLayout/sidebar/nav-main";
import { NavUser } from "@/components/dashboardLayout/sidebar/nav-user";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
} from "@/components/ui/sidebar";
import { AfdaLogo } from "./AfdaLogo";

export function AppSidebar({ side, ...props }: React.ComponentProps<typeof Sidebar>) {
  return (
    <Sidebar
      side={side ?? "left"}
      collapsible="icon"
      className="bg-card overflow-hidden"
      {...props}
    >
      <SidebarHeader>
        <AfdaLogo />
      </SidebarHeader>
      <SidebarContent className="bg-card">
        <NavMain />
      </SidebarContent>
      <SidebarFooter className="w-full">
        <NavUser />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
